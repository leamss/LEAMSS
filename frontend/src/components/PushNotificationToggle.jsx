import { Bell, BellOff, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import usePushNotifications from '@/hooks/usePushNotifications';

const PushNotificationToggle = ({ variant = 'button' }) => {
  const {
    isSupported,
    isSubscribed,
    permission,
    loading,
    error,
    subscribe,
    unsubscribe
  } = usePushNotifications();

  const handleToggle = async () => {
    if (isSubscribed) {
      const success = await unsubscribe();
      if (success) {
        toast.success('Push notifications disabled');
      } else {
        toast.error('Failed to disable push notifications');
      }
    } else {
      const success = await subscribe();
      if (success) {
        toast.success('Push notifications enabled! You will now receive alerts even when the portal is closed.');
      } else if (permission === 'denied') {
        toast.error('Notification permission was denied. Please enable notifications in your browser settings.');
      } else {
        toast.error('Failed to enable push notifications');
      }
    }
  };

  if (!isSupported) {
    return null; // Don't show anything if not supported
  }

  if (variant === 'switch') {
    return (
      <div className="flex items-center gap-3">
        <Switch
          checked={isSubscribed}
          onCheckedChange={handleToggle}
          disabled={loading || permission === 'denied'}
          data-testid="push-notification-switch"
        />
        <span className="text-sm text-slate-600">
          {isSubscribed ? 'Push notifications on' : 'Push notifications off'}
        </span>
        {loading && <Loader2 className="h-4 w-4 animate-spin text-slate-400" />}
      </div>
    );
  }

  return (
    <Button
      variant={isSubscribed ? 'outline' : 'default'}
      size="sm"
      onClick={handleToggle}
      disabled={loading || permission === 'denied'}
      className={isSubscribed ? 'border-green-500 text-green-600' : ''}
      data-testid="push-notification-button"
    >
      {loading ? (
        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
      ) : isSubscribed ? (
        <Bell className="h-4 w-4 mr-2" />
      ) : (
        <BellOff className="h-4 w-4 mr-2" />
      )}
      {isSubscribed ? 'Push On' : 'Enable Push'}
    </Button>
  );
};

export default PushNotificationToggle;
