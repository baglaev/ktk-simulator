import { useState } from 'react';
import { observer } from 'mobx-react-lite';
import { useNavigate } from 'react-router-dom';

import { Button } from '@consta/uikit/Button';
import { TextField } from '@consta/uikit/TextField';
import { Text } from '@consta/uikit/Text';

import styles from './LoginPage.module.css';
import { authStore } from '@/features/auth/model/auth.api.store';

export const LoginPage = observer(() => {
  const navigate = useNavigate();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = async () => {
    const path = await authStore.login(username, password);

    if (path) {
      navigate(path, {
        replace: true,
      });
    }
  };

  return (
    <main className={styles.page}>
      <div className={styles.form}>
        <Text size="2xl" weight="semibold">
          Авторизация
        </Text>

        <TextField
          label="Логин"
          value={username}
          onChange={(value) => setUsername(value ?? '')}
          placeholder="Введите логин"
        />

        <TextField
          label="Пароль"
          type="password"
          value={password}
          onChange={(value) => setPassword(value ?? '')}
          placeholder="Введите пароль"
        />

        {authStore.error && <Text view="alert">{authStore.error}</Text>}

        <Button
          label="Войти"
          loading={authStore.isLoading}
          disabled={!username || !password}
          onClick={handleLogin}
        />
      </div>
    </main>
  );
});

LoginPage.displayName = 'LoginPage';
