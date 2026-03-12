<script>
  import { Thermometer, Wind, Sun, Activity, Lock, Unlock, Car, Settings } from 'lucide-svelte';
  import { createEventDispatcher } from 'svelte';

  export let wifi;
  export let mqtt;
  export let systemStatus;

  const dispatch = createEventDispatcher();

  $: status = $systemStatus;

  function navigate(page) {
    dispatch('changePage', page);
  }

  async function fetchWithTimeout(resource, options = {}) {
    const { timeout = 5000 } = options;
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    try {
      const response = await fetch(resource, {
        ...options,
        signal: controller.signal
      });
      clearTimeout(id);
      return response;
    } catch (error) {
      clearTimeout(id);
      throw error;
    }
  }

  async function toggleDoor(side) {
    try {
      const response = await fetchWithTimeout(`/api/garage/${side}/toggle`, { method: 'POST' });
      if (!response.ok) throw new Error('Failed to toggle door');
      // Status will update via polling
    } catch (err) {
      console.error(`Error toggling ${side} door:`, err);
      alert(`Failed to toggle ${side} door`);
    }
  }

  function formatDist(m) {
    if (m === undefined) return 'N/A';
    return m.toFixed(2) + ' m';
  }
</script>

<div class="page">
  <h2 class="page-title">Garage Overview</h2>

  <!-- System Status Bar -->
  <div class="system-status-bar">
    <div class="stat-compact">
      <span class="stat-icon-inline temp-color">
        <Thermometer size={18} />
      </span>
      <span class="stat-text">{status.temperature ? status.temperature.toFixed(1) : '0.0'}°C</span>
    </div>

    <div class="stat-compact">
      <span class="stat-icon-inline humidity-color">
        <Wind size={18} />
      </span>
      <span class="stat-text">{status.humidity ? status.humidity.toFixed(1) : '0.0'}%</span>
    </div>

    <div class="stat-compact">
      <span class="stat-icon-inline light-color">
        <Sun size={18} />
      </span>
      <span class="stat-text">{status.light ? status.light.toFixed(0) : '0'}% Light</span>
    </div>

    <div class="stat-compact">
      <span class="stat-icon-inline motion-color" class:active={status.motion}>
        <Activity size={18} />
      </span>
      <span class="stat-text" class:status-warning={status.motion}>
        {status.motion ? 'Motion Detected' : 'No Motion'}
      </span>
    </div>
  </div>

  <div class="card-grid">
    <!-- Left Door Card -->
    <div class="door-card">
      <div class="card-header">
        <div class="door-icon" class:open={status.garage?.left?.open}>
          {#if status.garage?.left?.open}
            <Unlock size={32} />
          {:else}
            <Lock size={32} />
          {/if}
        </div>
        <div class="header-text">
          <div class="title-row">
            <h3>Left Door</h3>
            <button class="icon-btn" on:click={() => navigate('door-left')} title="Door Settings">
              <Settings size={20} />
            </button>
          </div>
          <div class="badge-row">
            <span class="status-badge" class:open={status.garage?.left?.open}>
              {status.garage?.left?.open ? 'OPEN' : 'CLOSED'}
            </span>
            <span class="presence-badge" class:present={status.garage?.left?.car}>
              <Car size={14} />
              {status.garage?.left?.car ? 'CAR' : 'EMPTY'}
            </span>
          </div>
        </div>
      </div>
      
      <div class="card-body">
        <div class="detail-row">
          <span class="label">Distance:</span>
          <span class="value">{formatDist(status.garage?.left?.dist)}</span>
        </div>
        <div class="detail-row">
          <span class="label">Car Present:</span>
          <span class="value" class:present={status.garage?.left?.car}>
            <Car size={18} class="inline-icon" />
            {status.garage?.left?.car ? 'YES' : 'NO'}
          </span>
        </div>
        <div class="detail-row">
          <span class="label">HMM Model:</span>
          <span class="value" class:active={status.garage?.left?.modelLoaded}>
            {status.garage?.left?.modelLoaded ? 'Active' : 'Inactive'}
          </span>
        </div>
      </div>

      <button class="toggle-btn" on:click={() => toggleDoor('left')}>
        Toggle Left Door
      </button>
    </div>

    <!-- Right Door Card -->
    <div class="door-card">
      <div class="card-header">
        <div class="door-icon" class:open={status.garage?.right?.open}>
          {#if status.garage?.right?.open}
            <Unlock size={32} />
          {:else}
            <Lock size={32} />
          {/if}
        </div>
        <div class="header-text">
          <div class="title-row">
            <h3>Right Door</h3>
            <button class="icon-btn" on:click={() => navigate('door-right')} title="Door Settings">
              <Settings size={20} />
            </button>
          </div>
          <div class="badge-row">
            <span class="status-badge" class:open={status.garage?.right?.open}>
              {status.garage?.right?.open ? 'OPEN' : 'CLOSED'}
            </span>
            <span class="presence-badge" class:present={status.garage?.right?.car}>
              <Car size={14} />
              {status.garage?.right?.car ? 'CAR' : 'EMPTY'}
            </span>
          </div>
        </div>
      </div>

      <div class="card-body">
        <div class="detail-row">
          <span class="label">Distance:</span>
          <span class="value">{formatDist(status.garage?.right?.dist)}</span>
        </div>
        <div class="detail-row">
          <span class="label">Car Present:</span>
          <span class="value" class:present={status.garage?.right?.car}>
            <Car size={18} class="inline-icon" />
            {status.garage?.right?.car ? 'YES' : 'NO'}
          </span>
        </div>
        <div class="detail-row">
          <span class="label">HMM Model:</span>
          <span class="value" class:active={status.garage?.right?.modelLoaded}>
            {status.garage?.right?.modelLoaded ? 'Active' : 'Inactive'}
          </span>
        </div>
      </div>

      <button class="toggle-btn" on:click={() => toggleDoor('right')}>
        Toggle Right Door
      </button>
    </div>
  </div>
</div>

<style>
  .page-title {
    font-size: 2rem;
    font-weight: 700;
    color: #1f2937;
    margin-bottom: 1.5rem;
  }

  .system-status-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 1.5rem;
    padding: 1rem;
    background: white;
    border-radius: 0.5rem;
    border: 1px solid #e5e7eb;
    margin-bottom: 1.5rem;
  }

  .stat-compact {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .stat-icon-inline.temp-color { color: #dc2626; }
  .stat-icon-inline.humidity-color { color: #2563eb; }
  .stat-icon-inline.light-color { color: #f59e0b; }
  .stat-icon-inline.motion-color { color: #6b7280; }
  .stat-icon-inline.motion-color.active { color: #ef4444; }

  .stat-text {
    font-size: 0.875rem;
    font-weight: 600;
    color: #1f2937;
  }

  .status-warning { color: #ef4444; }

  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
  }

  .door-card {
    background: white;
    padding: 1.5rem;
    border-radius: 0.75rem;
    border: 1px solid #e5e7eb;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    display: flex;
    flex-direction: column;
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .door-icon {
    width: 64px;
    height: 64px;
    border-radius: 1rem;
    background: #f3f4f6;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #6b7280;
  }

  .door-icon.open {
    background: #fef3c7;
    color: #d97706;
  }

  .header-text {
    flex: 1;
  }

  .title-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .header-text h3 {
    font-size: 1.25rem;
    font-weight: 700;
  }

  .icon-btn {
    background: none;
    border: none;
    color: #9ca3af;
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 0.375rem;
    transition: all 0.2s;
  }

  .icon-btn:hover {
    background: #f3f4f6;
    color: #3b82f6;
  }

  .badge-row {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .status-badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 9999px;
    font-size: 0.7rem;
    font-weight: 700;
    background: #e5e7eb;
    color: #4b5563;
  }

  .status-badge.open {
    background: #fef3c7;
    color: #92400e;
  }

  .presence-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.2rem 0.6rem;
    border-radius: 9999px;
    font-size: 0.7rem;
    font-weight: 700;
    background: #f3f4f6;
    color: #6b7280;
  }

  .presence-badge.present {
    background: #dbeafe;
    color: #1e40af;
  }

  .card-body {
    flex: 1;
    margin-bottom: 1.5rem;
  }

  .detail-row {
    display: flex;
    justify-content: space-between;
    padding: 0.75rem 0;
    border-bottom: 1px solid #f3f4f6;
  }

  .detail-row:last-child {
    border-bottom: none;
  }

  .label {
    color: #6b7280;
    font-size: 0.875rem;
  }

  .value {
    font-weight: 600;
    color: #1f2937;
  }

  .value.present {
    color: #059669;
  }

  .value.active {
    color: #3b82f6;
  }

  .inline-icon {
    vertical-align: middle;
    margin-right: 0.25rem;
  }

  .toggle-btn {
    width: 100%;
    padding: 0.75rem;
    background: #1f2937;
    color: white;
    border: none;
    border-radius: 0.5rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
  }

  .toggle-btn:hover {
    background: #374151;
  }

  .toggle-btn:active {
    transform: translateY(1px);
  }
</style>
