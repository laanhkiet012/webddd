import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import DisableDevtool from 'disable-devtool';

// Anti-debug configuration
if (import.meta.env.PROD) { // Only enable in production build
  DisableDevtool({
    ondevtoolopen: (type) => {
      document.body.innerHTML = `
        <div style="
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          height: 100vh;
          background: #09090b;
          color: #ef4444;
          font-family: monospace;
          text-align: center;
          z-index: 99999;
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
        ">
          <h1 style="font-size: 3rem; margin-bottom: 1rem;">🚫 DEBUGGING DETECTED</h1>
          <p style="font-size: 1.2rem; color: #a1a1aa;">Hệ thống phát hiện hành vi DevTools.</p>
          <p style="font-size: 1rem; color: #52525b; margin-top: 2rem;">IP của bạn đã được ghi lại.</p>
        </div>
      `;
    },
    disableMenu: true,     // Disable right click menu
    disableSelect: true,   // Disable text selection
    disableCopy: true,     // Disable copy
    disableCut: true,      // Disable cut
    disablePaste: true     // Disable paste
  });
}

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error("Could not find root element to mount to");
}

const root = ReactDOM.createRoot(rootElement);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);