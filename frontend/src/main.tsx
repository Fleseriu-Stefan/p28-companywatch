import { createRoot } from 'react-dom/client';

// Toolchain entry only. Visual UI remains blocked by D-002 and Q-004.
const container = document.getElementById('root');
if (container) {
  createRoot(container).render(null);
}
