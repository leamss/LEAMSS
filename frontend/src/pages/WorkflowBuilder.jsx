import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { toast } from 'sonner';
import { ArrowLeft, GripVertical, Plus, Trash2, Save, MoveUp, MoveDown, FileText, Edit } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import WorkflowIntakeEditor from "../components/WorkflowIntakeEditor";

const API = process.env.REACT_APP_BACKEND_URL ? `${process.env.REACT_APP_BACKEND_URL}/api` : '/api';


const WorkflowBuilder = () => {
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [selectedProductId, setSelectedProductId] = useState('');
  const [workflow, setWorkflow] = useState(null);
  const [steps, setSteps] = useState([]);
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);
  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    axios.get(`${API}/products`, { headers }).then(res => setProducts(res.data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedProductId) {
      axios.get(`${API}/workflows/${selectedProductId}`, { headers })
        .then(res => {
          setWorkflow(res.data);
          setSteps(res.data.steps || []);
          setHasChanges(false);
        })
        .catch(() => toast.error('Failed to load workflow'));
    }
  }, [selectedProductId]);

  const moveStep = (index, direction) => {
    const newSteps = [...steps];
    const swapIdx = direction === 'up' ? index - 1 : index + 1;
    if (swapIdx < 0 || swapIdx >= newSteps.length) return;
    [newSteps[index], newSteps[swapIdx]] = [newSteps[swapIdx], newSteps[index]];
    newSteps.forEach((s, i) => { s.order = i + 1; s.step_order = i + 1; });
    setSteps(newSteps);
    setHasChanges(true);
  };

  const addStep = () => {
    const newStep = {
      id: `new-${Date.now()}`,
      name: '',
      step_name: '',
      description: '',
      duration_days: 7,
      required_documents: [],
      order: steps.length + 1,
      step_order: steps.length + 1,
       sections: [],
      is_active: true,
      _isNew: true
    };
    setSteps([...steps, newStep]);
    setHasChanges(true);
  };

  const deleteStep = (index) => {
    const newSteps = steps.filter((_, i) => i !== index);
    newSteps.forEach((s, i) => { s.order = i + 1; s.step_order = i + 1; });
    setSteps(newSteps);
    setHasChanges(true);
  };

  const updateStep = (index, field, value) => {
    const newSteps = [...steps];
    newSteps[index] = { ...newSteps[index], [field]: value };
    if (field === 'name') newSteps[index].step_name = value;
    if (field === 'step_name') newSteps[index].name = value;
    setSteps(newSteps);
    setHasChanges(true);
  };
  const addSection = (stepIndex) => {

    const newSteps = [...steps];

    if(!newSteps[stepIndex].sections){

        newSteps[stepIndex].sections=[];

    }

    newSteps[stepIndex].sections.push({

        id:Date.now().toString(),

        title:"New Section",

        fields:[]

    });

    setSteps(newSteps);

    setHasChanges(true);

}
  const [expandedSteps, setExpandedSteps] = useState({});
  const toggleStep = (stepId) => {
    setExpandedSteps(prev => ({
        ...prev,
        [stepId]: !prev[stepId]
    }));
};
  const saveWorkflow = async () => {
    setSaving(true);
    try {
      const payload = steps.map(s => ({
        id: s._isNew ? undefined : s.id,
        name: s.name || s.step_name,
        step_name: s.step_name || s.name,
        description: s.description || '',
        duration_days: s.duration_days || 7,
        required_documents: s.required_documents || [],
        sections: s.sections || [],
        is_active: s.is_active !== false
      }));
      await axios.put(`${API}/workflows/${selectedProductId}`, { steps: payload }, { headers });
      toast.success('Workflow saved!');
      setHasChanges(false);
      // Reload
      const res = await axios.get(`${API}/workflows/${selectedProductId}`, { headers });
      setSteps(res.data.steps || []);
    } catch (error) {
      toast.error('Failed to save workflow');
    }
    setSaving(false);
  };


  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-[#2a777a] to-[#236466] text-white p-4 shadow-lg">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" className="text-white hover:bg-white/20" onClick={() => navigate(-1)} data-testid="back-btn">
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <h1 className="text-xl font-bold">Workflow Builder</h1>
          </div>
          {hasChanges && (
            <Button onClick={saveWorkflow} disabled={saving} className="bg-white text-[#2a777a] hover:bg-white/90" data-testid="save-workflow-btn">
              <Save className="h-4 w-4 mr-2" /> {saving ? 'Saving...' : 'Save Workflow'}
            </Button>
          )}
        </div>
      </header>

      <main className="max-w-5xl mx-auto p-6">
        {/* Product Selector */}
        <Card className="mb-6 p-6">
          <div className="flex items-center gap-4">
            <Label className="font-semibold whitespace-nowrap">Select Product:</Label>
            <Select value={selectedProductId} onValueChange={setSelectedProductId}>
              <SelectTrigger className="max-w-md" data-testid="workflow-product-select">
                <SelectValue placeholder="Choose a product..." />
              </SelectTrigger>
              <SelectContent>
                {products.map(p => (
                  <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </Card>

        {/* Workflow Steps */}
        {selectedProductId && (
          <div className="space-y-3">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-slate-800">
                {workflow?.product_name} — {steps.length} Steps
              </h2>
              <Button onClick={addStep} className="bg-[#2a777a] hover:bg-[#236466]" data-testid="add-step-btn">
                <Plus className="h-4 w-4 mr-2" /> Add Step
              </Button>
            </div>

           {steps.map((step, idx) => (
  <Card
    key={step.id || idx}
    className={`p-4 border-l-4 ${
      step._isNew
        ? "border-l-amber-500 bg-amber-50/50"
        : "border-l-[#2a777a]"
    }`}
    data-testid={`step-card-${idx}`}
  >
    {/* Step Header */}
    <div className="flex items-start gap-3">
      {/* Drag Handle */}
      <div className="flex flex-col items-center gap-1 pt-2">
        <GripVertical className="h-5 w-5 text-slate-400" />
        <span className="text-xs font-bold text-[#2a777a] bg-[#2a777a]/10 rounded-full w-6 h-6 flex items-center justify-center">
          {idx + 1}
        </span>
      </div>

      {/* Step Details */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-3">
        <div>
          <Label className="text-xs">Step Name</Label>
          <Input
            value={step.name || step.step_name || ""}
            onChange={(e) => updateStep(idx, "name", e.target.value)}
            placeholder="Step name..."
            data-testid={`step-name-${idx}`}
          />
        </div>

        <div>
          <Label className="text-xs">Duration (days)</Label>
          <Input
            type="number"
            value={step.duration_days || 7}
            onChange={(e) =>
              updateStep(idx, "duration_days", parseInt(e.target.value) || 7)
            }
          />
        </div>

        <div>
          <Label className="text-xs">Description</Label>
          <Input
            value={step.description || ""}
            onChange={(e) =>
              updateStep(idx, "description", e.target.value)
            }
            placeholder="Brief description..."
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-col gap-1">
        <Button
          size="sm"
          variant="ghost"
          onClick={() => moveStep(idx, "up")}
          disabled={idx === 0}
        >
          <MoveUp className="h-4 w-4" />
        </Button>

        <Button
          size="sm"
          variant="ghost"
          onClick={() => moveStep(idx, "down")}
          disabled={idx === steps.length - 1}
        >
          <MoveDown className="h-4 w-4" />
        </Button>

        <Button
          size="sm"
          variant="ghost"
          className="text-red-500 hover:text-red-700"
          onClick={() => deleteStep(idx)}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>

    {/* ================= Intake Form ================= */}

    <div className="mt-6 border-t pt-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-[#2a777a]" />
          <h3 className="font-semibold text-slate-800">
            Intake Form
          </h3>
        </div>

        <Button
    variant="outline"
    size="sm"
    onClick={() => toggleStep(step.id)}
>
    {expandedSteps[step.id]
        ? "Hide Intake Form"
        : "Configure Intake Form"}
</Button>
      </div>

      <div className="mt-3 rounded-lg border border-dashed bg-slate-50 p-4">

{!expandedSteps[step.id] ? (

  <p className="text-sm text-slate-500">
    {step.sections?.length
      ? `${step.sections.length} section(s) configured`
      : "This step doesn't have any intake sections yet."
    }
  </p>

) : (

  <WorkflowIntakeEditor
    sections={step.sections || []}
    onChange={(updatedSections) => {
      const newSteps = [...steps];
      newSteps[idx].sections = updatedSections;
      setSteps(newSteps);
      setHasChanges(true);
    }}
  />

)}

    {/* <div>

      <Button
        className="mb-3"
        size="sm"
        onClick={() => addSection(idx)}
      >
        <Plus className="h-4 w-4 mr-2" />
        Add Section
      </Button>

      {step.sections?.map((section, sectionIndex) => (
        <Card
          key={section.id}
          className="mb-3 p-3"
        >
          <Label className="mb-2 block">
            Section Name
          </Label>

          <Input
            value={section.title}
            onChange={(e) => {
              const newSteps = [...steps];

              newSteps[idx].sections[sectionIndex].title =
                e.target.value;

              setSteps(newSteps);
              setHasChanges(true);
            }}
          />
        </Card>
      ))}

    </div> */}

  

</div>
    </div>
  </Card>
))}

            {steps.length === 0 && (
              <Card className="p-12 text-center">
                <FileText className="h-12 w-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-600 font-medium">No steps configured</p>
                <p className="text-sm text-slate-500">Click "Add Step" to build your workflow</p>
              </Card>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default WorkflowBuilder;
