import { User } from '@consta/uikit/User';
import { Text } from '@consta/uikit/Text';
import { Picture } from '@consta/uikit/Picture';
import { Button } from '@consta/uikit/Button';

import { IconExit } from '@consta/icons/IconExit';

import { observer } from 'mobx-react-lite';

import { useNavigate } from 'react-router-dom';

import { authStore } from '@/features/auth/model/auth.api.store';

import styles from './Header.module.css';

interface Props {
  userName?: string;
  userInfo?: string;
}

export const Header = observer((props: Props) => {
  const { userName = 'Демо-профиль', userInfo = 'Обучаемый' } = props;

  const navigate = useNavigate();

  const handleLogout = () => {
    authStore.logout();

    navigate('/login', {
      replace: true,
    });
  };

  return (
    <header className={styles.header}>
      <div className={styles.titleContainer}>
        <Picture src="../../../../public/logo.png" className={styles.logo} />

        <div>
          <Text size="l">Компьютерный тренажёрный комплекс</Text>

          <Text size="l" view="secondary">
            ЭЛОУ-АВТ
          </Text>
        </div>
      </div>

      <div className={styles.userContainer}>
        <User name={userName} info={userInfo} size="l" />

        <Button onlyIcon view="ghost" iconLeft={IconExit} onClick={handleLogout} />
      </div>
    </header>
  );
});

Header.displayName = 'Header';
