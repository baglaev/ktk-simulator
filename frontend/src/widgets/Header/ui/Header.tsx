import { User } from '@consta/uikit/User';
import { Text } from '@consta/uikit/Text';
import { Picture } from '@consta/uikit/Picture';

import styles from './Header.module.css';

export const Header = () => {
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
      <User name="Демо-профиль" info="Обучаемый" size="l" />
    </header>
  );
};

Header.displayName = 'Header';
