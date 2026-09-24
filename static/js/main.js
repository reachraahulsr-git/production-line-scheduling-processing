// Global Application JavaScript
document.addEventListener('keydown', function(event) {
  if (event.key === "Escape") {
    const modals = document.querySelectorAll('.modal-overlay');
    modals.forEach(m => m.style.display = 'none');
  }
});

// Auto-dismiss alerts after 5 seconds
setTimeout(() => {
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(a => {
    a.style.transition = "opacity 0.5s ease";
    a.style.opacity = "0";
    setTimeout(() => a.remove(), 500);
  });
}, 5000);
