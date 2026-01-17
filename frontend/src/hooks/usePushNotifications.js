import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Convert base64 URL to Uint8Array for VAPID key
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export function usePushNotifications() {
  const [isSupported, setIsSupported] = useState(false);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [permission, setPermission] = useState('default');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const initializedRef = useRef(false);

  const getAuthHeader = useCallback(() => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }), []);

  // Initialize on mount - check support and subscription
  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;

    const supported = 'serviceWorker' in navigator && 'PushManager' in window;
    setIsSupported(supported);
    
    if (supported && 'Notification' in window) {
      setPermission(Notification.permission);
      
      // Check subscription status
      navigator.serviceWorker.ready.then(registration => {
        registration.pushManager.getSubscription().then(subscription => {
          setIsSubscribed(!!subscription);
        }).catch(err => {
          console.error('Error checking subscription:', err);
        });
      }).catch(err => {
        console.error('Service worker not ready:', err);
      });
    }
  }, []);

  // Check current subscription status
  const checkSubscription = useCallback(async () => {
    const supported = 'serviceWorker' in navigator && 'PushManager' in window;
    if (!supported) return false;

    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      setIsSubscribed(!!subscription);
      return !!subscription;
    } catch (err) {
      console.error('Error checking subscription:', err);
      return false;
    }
  }, []);

  // Register service worker
  const registerServiceWorker = useCallback(async () => {
    if (!isSupported) return null;

    try {
      const registration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/'
      });
      console.log('Service Worker registered:', registration);
      return registration;
    } catch (err) {
      console.error('Service Worker registration failed:', err);
      setError('Failed to register service worker');
      return null;
    }
  }, [isSupported]);

  // Subscribe to push notifications
  const subscribe = useCallback(async () => {
    if (!isSupported) {
      setError('Push notifications are not supported');
      return false;
    }

    setLoading(true);
    setError(null);

    try {
      // Request notification permission
      const permissionResult = await Notification.requestPermission();
      setPermission(permissionResult);

      if (permissionResult !== 'granted') {
        setError('Notification permission denied');
        setLoading(false);
        return false;
      }

      // Register service worker
      const registration = await registerServiceWorker();
      if (!registration) {
        setLoading(false);
        return false;
      }

      await navigator.serviceWorker.ready;

      // Get VAPID public key from server
      const keyResponse = await axios.get(`${API}/push/vapid-public-key`, getAuthHeader());
      const vapidPublicKey = keyResponse.data.publicKey;

      // Subscribe to push manager
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
      });

      // Send subscription to server
      const subscriptionJson = subscription.toJSON();
      await axios.post(`${API}/push/subscribe`, {
        endpoint: subscriptionJson.endpoint,
        keys: subscriptionJson.keys
      }, getAuthHeader());

      setIsSubscribed(true);
      setLoading(false);
      return true;
    } catch (err) {
      console.error('Failed to subscribe:', err);
      setError(err.response?.data?.detail || 'Failed to subscribe to push notifications');
      setLoading(false);
      return false;
    }
  }, [isSupported, getAuthHeader, registerServiceWorker]);

  // Unsubscribe from push notifications
  const unsubscribe = useCallback(async () => {
    if (!isSupported) return false;

    setLoading(true);
    setError(null);

    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();

      if (subscription) {
        // Unsubscribe from push manager
        await subscription.unsubscribe();

        // Remove subscription from server
        await axios.delete(`${API}/push/unsubscribe?endpoint=${encodeURIComponent(subscription.endpoint)}`, getAuthHeader());
      }

      setIsSubscribed(false);
      setLoading(false);
      return true;
    } catch (err) {
      console.error('Failed to unsubscribe:', err);
      setError(err.response?.data?.detail || 'Failed to unsubscribe');
      setLoading(false);
      return false;
    }
  }, [isSupported, getAuthHeader]);

  return {
    isSupported,
    isSubscribed,
    permission,
    loading,
    error,
    subscribe,
    unsubscribe,
    checkSubscription
  };
}

export default usePushNotifications;
