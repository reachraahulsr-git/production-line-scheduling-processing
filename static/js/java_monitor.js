// Java Thread Monitor Live Polling & Control Client
let pollInterval = null;

function fetchLiveStatus() {
  fetch('/api/java/status')
    .then(res => res.json())
    .then(data => {
      if (data.is_offline) {
        const textEl = document.getElementById('engineStatusText');
        if (textEl) textEl.textContent = 'OFFLINE (Starting...)';
        return;
      }

      // Update Header
      const statusText = document.getElementById('engineStatusText');
      if (statusText) {
        statusText.textContent = data.isPaused ? 'PAUSED' : (data.isRunning ? 'RUNNING' : 'ONLINE');
        statusText.style.color = data.isPaused ? 'var(--warning)' : 'var(--primary)';
      }

      const activeCount = document.getElementById('activeThreadsCount');
      if (activeCount) {
        activeCount.textContent = `${data.activeMachineThreads} Active Threads`;
      }

      // Update Individual Threads
      if (data.threads && data.threads.length > 0) {
        data.threads.forEach(th => {
          const mId = th.machine.id;
          const stateEl = document.getElementById(`thread-state-${mId}`);
          if (stateEl) {
            stateEl.textContent = th.machine.state;
            stateEl.className = `status-badge ${th.machine.state}`;
          }

          const taskEl = document.getElementById(`active-task-${mId}`);
          const barEl = document.getElementById(`thread-progress-${mId}`);
          const pctEl = document.getElementById(`thread-progress-pct-${mId}`);

          if (th.activeJob) {
            if (taskEl) taskEl.textContent = `${th.activeJob.jobNumber}: ${th.activeJob.title}`;
            if (barEl) barEl.style.width = `${th.activeJob.progress}%`;
            if (pctEl) pctEl.textContent = `${th.activeJob.progress}%`;
          } else {
            if (taskEl) taskEl.innerHTML = '<span style="color: #94a3b8; font-style: italic;">Thread Idle (Waiting)</span>';
            if (barEl) barEl.style.width = '0%';
            if (pctEl) pctEl.textContent = '0%';
          }

          const qEl = document.getElementById(`queue-depth-${mId}`);
          if (qEl) qEl.textContent = th.queueDepth;
        });
      }

      // Update Console Output
      if (data.events && data.events.length > 0) {
        const consoleEl = document.getElementById('javaConsole');
        if (consoleEl) {
          const lines = data.events.map(ev => {
            const time = ev.timestamp ? ev.timestamp.substring(11, 19) : '';
            return `<div><span style="color: #94a3b8;">[${time}]</span> <span style="color: #38bdf8;">[${ev.threadName}]</span> ${ev.message}</div>`;
          }).join('');
          consoleEl.innerHTML = lines;
        }
      }
    })
    .catch(err => console.error("Poll error:", err));
}

function dispatchBatchToJava() {
  fetch('/api/java/dispatch', { method: 'POST' })
    .then(res => res.json())
    .then(data => {
      fetchLiveStatus();
    });
}

function pauseJavaEngine() {
  fetch('/api/java/pause', { method: 'POST' }).then(() => fetchLiveStatus());
}

function resumeJavaEngine() {
  fetch('/api/java/resume', { method: 'POST' }).then(() => fetchLiveStatus());
}

function stopJavaEngine() {
  if (confirm("Are you sure you want to stop all active machine threads?")) {
    fetch('/api/java/stop', { method: 'POST' }).then(() => fetchLiveStatus());
  }
}

// Auto-start polling on page load
document.addEventListener('DOMContentLoaded', () => {
  fetchLiveStatus();
  pollInterval = setInterval(fetchLiveStatus, 1500);
});

window.addEventListener('beforeunload', () => {
  if (pollInterval) clearInterval(pollInterval);
});
