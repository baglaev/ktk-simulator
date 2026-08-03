import { useEffect } from 'react';
import { AppRouter } from '@/app/router/AppRouter';
import { Theme, presetGpnDark } from '@consta/uikit/Theme';

import './App.css';

function App() {
  useEffect(() => {
    document.documentElement.classList.add('theme-dark');
  }, []);

  return (
    <Theme preset={presetGpnDark}>
      <AppRouter />
    </Theme>
  );
}

export default App;
