<script>
  import { FileUp, CheckCircle, XCircle, BrainCircuit } from 'lucide-svelte';

  export let systemStatus;
  $: status = $systemStatus;

  let uploading = { left: false, right: false };
  let messages = { left: '', right: '' };
  let files = { left: null, right: null };

  async function uploadModel(side) {
    if (!files[side]) {
      messages[side] = 'Please select a file first';
      return;
    }

    uploading[side] = true;
    messages[side] = '';

    const formData = new FormData();
    formData.append('model', files[side]);

    try {
      const response = await fetch(`/upload_${side}`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) throw new Error('Upload failed');

      messages[side] = 'Model uploaded successfully!';
      files[side] = null;
      // Reset the file input
      const input = document.getElementById(`file-${side}`);
      if (input) input.value = '';
      
    } catch (err) {
      console.error(`Error uploading ${side} model:`, err);
      messages[side] = `Error: ${err.message}`;
    } finally {
      uploading[side] = false;
    }
  }

  function handleFileChange(event, side) {
    files[side] = event.target.files[0];
    messages[side] = '';
  }
</script>

<div class="page">
  <h2 class="page-title">HMM Model Management</h2>
  <p class="page-description">
    Upload Hidden Markov Model (HMM) configuration files (JSON) to improve door state detection accuracy.
  </p>

  <div class="card-grid">
    <!-- Left Model Card -->
    <div class="model-card">
      <div class="card-header">
        <BrainCircuit size={24} class="text-blue-600" />
        <h3>Left Door Model</h3>
        <div class="model-status" class:loaded={status.garage?.left?.modelLoaded}>
          {status.garage?.left?.modelLoaded ? 'ACTIVE' : 'NOT LOADED'}
        </div>
      </div>

      <div class="upload-section">
        <label class="file-label" for="file-left">
          <input 
            type="file" 
            id="file-left" 
            accept=".json"
            on:change={(e) => handleFileChange(e, 'left')}
          />
          <div class="file-custom">
            <FileUp size={20} />
            <span>{files.left ? files.left.name : 'Choose JSON file...'}</span>
          </div>
        </label>

        <button 
          class="btn btn-primary" 
          disabled={uploading.left || !files.left}
          on:click={() => uploadModel('left')}
        >
          {uploading.left ? 'Uploading...' : 'Upload Left Model'}
        </button>

        {#if messages.left}
          <div class="message" class:error={messages.left.startsWith('Error')}>
            {#if messages.left.startsWith('Error')}
              <XCircle size={16} />
            {:else}
              <CheckCircle size={16} />
            {/if}
            {messages.left}
          </div>
        {/if}
      </div>
    </div>

    <!-- Right Model Card -->
    <div class="model-card">
      <div class="card-header">
        <BrainCircuit size={24} class="text-blue-600" />
        <h3>Right Door Model</h3>
        <div class="model-status" class:loaded={status.garage?.right?.modelLoaded}>
          {status.garage?.right?.modelLoaded ? 'ACTIVE' : 'NOT LOADED'}
        </div>
      </div>

      <div class="upload-section">
        <label class="file-label" for="file-right">
          <input 
            type="file" 
            id="file-right" 
            accept=".json"
            on:change={(e) => handleFileChange(e, 'right')}
          />
          <div class="file-custom">
            <FileUp size={20} />
            <span>{files.right ? files.right.name : 'Choose JSON file...'}</span>
          </div>
        </label>

        <button 
          class="btn btn-primary" 
          disabled={uploading.right || !files.right}
          on:click={() => uploadModel('right')}
        >
          {uploading.right ? 'Uploading...' : 'Upload Right Model'}
        </button>

        {#if messages.right}
          <div class="message" class:error={messages.right.startsWith('Error')}>
            {#if messages.right.startsWith('Error')}
              <XCircle size={16} />
            {:else}
              <CheckCircle size={16} />
            {/if}
            {messages.right}
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  .page-title {
    font-size: 2rem;
    font-weight: 700;
    color: #1f2937;
    margin-bottom: 0.5rem;
  }

  .page-description {
    color: #6b7280;
    margin-bottom: 2rem;
    max-width: 600px;
  }

  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
    gap: 1.5rem;
  }

  .model-card {
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
  }

  .card-header h3 {
    font-size: 1.25rem;
    font-weight: 600;
    flex: 1;
  }

  .model-status {
    padding: 0.25rem 0.6rem;
    border-radius: 9999px;
    font-size: 0.7rem;
    font-weight: 700;
    background: #fee2e2;
    color: #991b1b;
  }

  .model-status.loaded {
    background: #d1fae5;
    color: #065f46;
  }

  .upload-section {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .file-label {
    cursor: pointer;
  }

  .file-label input {
    display: none;
  }

  .file-custom {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    background: #f9fafb;
    border: 2px dashed #d1d5db;
    border-radius: 0.5rem;
    color: #4b5563;
    transition: all 0.2s;
  }

  .file-label:hover .file-custom {
    border-color: #3b82f6;
    background: #eff6ff;
    color: #2563eb;
  }

  .btn {
    padding: 0.75rem;
    border: none;
    border-radius: 0.5rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
  }

  .btn-primary {
    background: #3b82f6;
    color: white;
  }

  .btn-primary:hover {
    background: #2563eb;
  }

  .btn-primary:disabled {
    background: #9ca3af;
    cursor: not-allowed;
  }

  .message {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    font-weight: 500;
    color: #059669;
    padding: 0.5rem;
    background: #ecfdf5;
    border-radius: 0.375rem;
  }

  .message.error {
    color: #dc2626;
    background: #fef2f2;
  }

  :global(.text-blue-600) {
    color: #2563eb;
  }
</style>
