import { createRoot } from 'react-dom/client';

// Toolchain entry pending implementation of the approved Draft 1 design (Q-004).
const container = document.getElementById('root');
if (container) {
  createRoot(container).render(null);
}
