<script>
  import { writable } from 'svelte/store';
  import { onMount } from 'svelte';
  import Navbar from './components/Navbar.svelte';
  import Sidebar from './components/Sidebar.svelte';
  import GaragePage from './pages/GaragePage.svelte';
  import DoorDetailPage from './pages/DoorDetailPage.svelte';
  import ModelsPage from './pages/ModelsPage.svelte';
  import WiFiConfigPage from './pages/WiFiConfigPage.svelte';
  import MQTTConfigPage from './pages/MQTTConfigPage.svelte';

  // API base URL
  const API_BASE = '/api';

  let currentPage = 'home';
  let loading = true;
  let error = null;

  export let wifi = writable({
    essid: '',
    password: '',
    board: 'garage133'
  });

  export let mqtt = writable({
    host: '',
    port: 1883,
    user: '',
    password: '',
    enabled: false
  });

  export let systemStatus = writable({
    temperature: 0,
    humidity: 0,
    light: 0,
    motion: false,
    mqttConnected: false,
    software: '',
    hardware: '',
    garage: {
      left: { open: false, car: false, dist: 0 },
      right: { open: false, car: false, dist: 0 }
    }
  });

  export let isOnline = writable(true);

  let isUpdating = false;

  async function fetchWithTimeout(resource, options = {}) {
    const { timeout = 4000 } = options;
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

  // Load WiFi config from server
  async function loadWiFiConfig() {
    try {
      const response = await fetchWithTimeout(`${API_BASE}/wifi`);
      if (!response.ok) throw new Error('Failed to load WiFi config');
      const data = await response.json();
      wifi.set(data);
      isOnline.set(true);
    } catch (err) {
      console.error('Error loading WiFi config:', err);
      isOnline.set(false);
    }
  }

  // Load MQTT config from server
  async function loadMQTTConfig() {
    try {
      const response = await fetchWithTimeout(`${API_BASE}/mqtt`);
      if (!response.ok) throw new Error('Failed to load MQTT config');
      const data = await response.json();
      mqtt.set(data);
      isOnline.set(true);
    } catch (err) {
      console.error('Error loading MQTT config:', err);
      isOnline.set(false);
    }
  }

  // Load system status
  async function loadSystemStatus() {
    if (isUpdating) return;
    isUpdating = true;
    try {
      const response = await fetchWithTimeout(`${API_BASE}/status`);
      if (!response.ok) throw new Error('Failed to load system status');
      const data = await response.json();
      systemStatus.set(data);
      isOnline.set(true);
    } catch (err) {
      console.error('Error loading system status:', err);
      isOnline.set(false);
    } finally {
      isUpdating = false;
    }
  }

  // Initialize data on mount
  onMount(async () => {
    loading = true;
    try {
      await Promise.all([
        loadWiFiConfig(),
        loadMQTTConfig(),
        loadSystemStatus()
      ]);
      loading = false;
    } catch (err) {
      error = err.message;
      loading = false;
    }

    // Polling mechanism
    let timer;
    async function poll() {
      await loadSystemStatus();
      timer = setTimeout(poll, 5000);
    }

    poll();

    return () => clearTimeout(timer);
  });

  function changePage(page) {
    currentPage = page;
  }
</script>

<div class="app-container">
  <Navbar {wifi} {isOnline} />
  {#if loading}
    <div class="loading-container">
      <div class="spinner"></div>
      <p>Loading Garage Control...</p>
    </div>
  {:else if error}
    <div class="error-container">
      <p class="error-message">⚠️ {error}</p>
      <p class="error-hint">Check device connection.</p>
    </div>
  {/if}
  <div class="main-layout" class:hidden={loading}>
    <Sidebar {currentPage} {systemStatus} on:changePage={(e) => changePage(e.detail)} />
    <main class="content">
      <div class="content-inner">
        {#if currentPage === 'home'}
          <GaragePage {wifi} {mqtt} {systemStatus} on:changePage={(e) => changePage(e.detail)} />
        {:else if currentPage === 'door-left'}
          <DoorDetailPage side="left" {systemStatus} on:changePage={(e) => changePage(e.detail)} />
        {:else if currentPage === 'door-right'}
          <DoorDetailPage side="right" {systemStatus} on:changePage={(e) => changePage(e.detail)} />
        {:else if currentPage === 'models'}
          <ModelsPage {systemStatus} />
        {:else if currentPage === 'wifi'}
          <WiFiConfigPage {wifi} />
        {:else if currentPage === 'mqtt'}
          <MQTTConfigPage {mqtt} {systemStatus} />
        {/if}
      </div>
    </main>
  </div>
</div>

<style>
  :global(*) {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  :global(body) {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    background: #f3f4f6;
    margin: 0;
    padding: 0;
  }

  .app-container {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .main-layout {
    display: flex;
    flex: 1;
  }

  @media (max-width: 768px) {
    .main-layout {
      flex-direction: column;
    }
  }

  .content {
    flex: 1;
    padding: 2rem;
  }

  @media (max-width: 768px) {
    .content {
      padding: 1rem;
    }
  }

  .content-inner {
    max-width: 1000px;
  }

  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 400px;
    gap: 1rem;
  }

  .spinner {
    width: 48px;
    height: 48px;
    border: 4px solid #e5e7eb;
    border-top-color: #059669;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .loading-container p {
    color: #6b7280;
    font-size: 1rem;
  }

  .error-container {
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 0.5rem;
    padding: 1.5rem;
    margin: 2rem;
    text-align: center;
  }

  .error-message {
    color: #991b1b;
    font-weight: 600;
    margin-bottom: 0.5rem;
  }

  .error-hint {
    color: #6b7280;
    font-size: 0.875rem;
  }

  .hidden {
    display: none;
  }
</style>
