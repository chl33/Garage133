<script>
  import { 
    Thermometer, Lock, Unlock, Car, BrainCircuit, FileUp, 
    CheckCircle, XCircle, ArrowLeft, Info
  } from 'lucide-svelte';
  import { createEventDispatcher } from 'svelte';

  export let side; // 'left' or 'right'
  export let systemStatus;
  
  const dispatch = createEventDispatcher();
  $: status = $systemStatus;
  $: doorData = status.garage?.[side];

  let uploading = false;
  let uploadMessage = '';
  let file = null;

  const stateLabels = [
    { id: 0, label: 'Open', color: '#fef3c7' },
    { id: 1, label: 'Closed (Car)', color: '#dcfce7' },
    { id: 2, label: 'Closed (Empty)', color: '#eff6ff' }
  ];

  async function toggleDoor() {
    try {
      await fetch(`/api/garage/${side}/toggle`, { method: 'POST' });
    } catch (err) {
      console.error('Toggle failed:', err);
    }
  }

  async function correctState(stateId) {
    try {
      const response = await fetch('/api/garage/label', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ side, state: stateId })
      });
      if (!response.ok) throw new Error('Correction failed');
    } catch (err) {
      alert('Error correcting state: ' + err.message);
    }
  }

  async function uploadModel() {
    if (!file) return;
    uploading = true;
    uploadMessage = '';

    const formData = new FormData();
    formData.append('model', file);

    try {
      const response = await fetch(`/upload_${side}`, {
        method: 'POST',
        body: formData
      });
      if (!response.ok) throw new Error('Upload failed');
      uploadMessage = 'Model updated successfully';
      file = null;
    } catch (err) {
      uploadMessage = 'Error: ' + err.message;
    } finally {
      uploading = false;
    }
  }

  function goBack() {
    dispatch('changePage', 'home');
  }
</script>

<div class="page">
  <div class="header-nav">
    <button class="back-btn" on:click={goBack}>
      <ArrowLeft size={20} />
      <span>Back to Overview</span>
    </button>
  </div>

  <h2 class="page-title capitalize">{side} Door Details</h2>

  <div class="detail-grid">
    <!-- Status Card -->
    <div class="card status-card">
      <div class="card-header">
        <Info size={24} />
        <h3>Current Status</h3>
      </div>
      
      <div class="status-main">
        <div class="large-icon" class:open={doorData?.open}>
          {#if doorData?.open}
            <Unlock size={48} />
          {:else}
            <Lock size={48} />
          {/if}
        </div>
        <div class="status-info">
          <div class="status-val" class:open={doorData?.open}>
            {doorData?.open ? 'OPEN' : 'CLOSED'}
          </div>
          <div class="dist-val">{doorData?.dist?.toFixed(3) || '0.000'} meters</div>
        </div>
      </div>

      <div class="presence-indicator" class:present={doorData?.car}>
        <Car size={20} />
        <span>Car {doorData?.car ? 'Detected' : 'Not Present'}</span>
      </div>

      <button class="action-btn toggle" on:click={toggleDoor}>
        Toggle Door Relay
      </button>
    </div>

    <!-- HMM Probabilities Card -->
    <div class="card hmm-card">
      <div class="card-header">
        <BrainCircuit size={24} />
        <h3>Detection Logic (HMM)</h3>
        <span class="badge" class:active={doorData?.modelLoaded}>
          {doorData?.modelLoaded ? 'Model Active' : 'No Model'}
        </span>
      </div>

      <div class="prob-list">
        {#if doorData?.probs && doorData.probs.length > 0}
          {#each stateLabels as state, i}
            <div class="prob-row">
              <div class="prob-label">
                <span class="state-dot" style="background: {state.color}"></span>
                {state.label}
              </div>
              <div class="prob-bar-container">
                <div 
                  class="prob-bar" 
                  style="width: {(doorData.probs[i] * 100).toFixed(1)}%; background: {state.color}"
                ></div>
                <span class="prob-text">{(doorData.probs[i] * 100).toFixed(1)}%</span>
              </div>
            </div>
          {/each}
        {:else}
          <p class="empty-msg">No probability data available. Is a model loaded?</p>
        {/if}
      </div>

      <div class="correction-section">
        <h4>Correct Current State</h4>
        <p class="hint">Manual correction resets HMM probabilities to 100% for the selected state.</p>
        <div class="btn-group">
          {#each stateLabels as state}
            <button class="btn-small" on:click={() => correctState(state.id)}>
              {state.label}
            </button>
          {/each}
        </div>
      </div>
    </div>

    <!-- Model Upload Card -->
    <div class="card upload-card">
      <div class="card-header">
        <FileUp size={24} />
        <h3>Update Model</h3>
      </div>
      
      <div class="upload-box">
        <input 
          type="file" 
          id="detail-file" 
          accept=".json"
          on:change={(e) => file = e.target.files[0]} 
          style="display:none"
        />
        <label for="detail-file" class="file-drop">
          {file ? file.name : 'Select HMM JSON file'}
        </label>
        
        <button 
          class="action-btn upload" 
          disabled={!file || uploading}
          on:click={uploadModel}
        >
          {uploading ? 'Uploading...' : 'Upload & Reload Model'}
        </button>
        
        {#if uploadMessage}
          <div class="msg" class:err={uploadMessage.startsWith('Error')}>
            {uploadMessage}
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  .capitalize { text-transform: capitalize; }
  
  .header-nav {
    margin-bottom: 1rem;
  }

  .back-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: none;
    border: none;
    color: #6b7280;
    cursor: pointer;
    font-weight: 500;
  }

  .back-btn:hover { color: #1f2937; }

  .page-title {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 2rem;
  }

  .detail-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 1.5rem;
  }

  .card {
    background: white;
    padding: 1.5rem;
    border-radius: 0.75rem;
    border: 1px solid #e5e7eb;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1.5rem;
    color: #374151;
  }

  .card-header h3 { font-size: 1.25rem; font-weight: 600; flex: 1; }

  .status-main {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    margin-bottom: 1.5rem;
  }

  .large-icon {
    width: 80px;
    height: 80px;
    background: #f3f4f6;
    border-radius: 1rem;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #6b7280;
  }

  .large-icon.open { background: #fef3c7; color: #d97706; }

  .status-val { font-size: 1.5rem; font-weight: 800; color: #4b5563; }
  .status-val.open { color: #d97706; }
  .dist-val { font-size: 1rem; color: #9ca3af; }

  .presence-indicator {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem;
    background: #f9fafb;
    border-radius: 0.5rem;
    margin-bottom: 1.5rem;
    font-weight: 600;
    color: #6b7280;
  }

  .presence-indicator.present { background: #dcfce7; color: #166534; }

  .action-btn {
    width: 100%;
    padding: 0.75rem;
    border: none;
    border-radius: 0.5rem;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s;
  }

  .action-btn.toggle { background: #1f2937; color: white; }
  .action-btn.upload { background: #3b82f6; color: white; margin-top: 1rem; }
  .action-btn:disabled { background: #d1d5db; cursor: not-allowed; }

  .badge {
    padding: 0.25rem 0.5rem;
    border-radius: 9999px;
    font-size: 0.7rem;
    font-weight: 700;
    background: #f3f4f6;
    color: #6b7280;
  }
  .badge.active { background: #d1fae5; color: #065f46; }

  .prob-list { margin-bottom: 2rem; }

  .prob-row { margin-bottom: 1rem; }
  .prob-label { font-size: 0.875rem; font-weight: 500; margin-bottom: 0.25rem; display: flex; align-items: center; gap: 0.5rem; }
  .state-dot { width: 8px; height: 8px; border-radius: 50%; }

  .prob-bar-container {
    height: 1.5rem;
    background: #f3f4f6;
    border-radius: 0.25rem;
    position: relative;
    overflow: hidden;
  }

  .prob-bar { height: 100%; transition: width 0.3s ease; }
  .prob-text { position: absolute; right: 0.5rem; top: 50%; transform: translateY(-50%); font-size: 0.75rem; font-weight: 700; }

  .correction-section h4 { font-size: 0.9rem; font-weight: 700; margin-bottom: 0.5rem; }
  .hint { font-size: 0.75rem; color: #9ca3af; margin-bottom: 1rem; }

  .btn-group { display: flex; gap: 0.5rem; }
  .btn-small { flex: 1; padding: 0.5rem; border: 1px solid #d1d5db; background: white; border-radius: 0.375rem; font-size: 0.75rem; font-weight: 600; cursor: pointer; }
  .btn-small:hover { background: #f9fafb; border-color: #9ca3af; }

  .file-drop {
    display: block;
    padding: 2rem;
    border: 2px dashed #d1d5db;
    border-radius: 0.5rem;
    text-align: center;
    color: #6b7280;
    cursor: pointer;
  }

  .msg { margin-top: 1rem; font-size: 0.875rem; color: #059669; }
  .msg.err { color: #dc2626; }

  @media (max-width: 768px) {
    .detail-grid { grid-template-columns: 1fr; }
  }
</style>
