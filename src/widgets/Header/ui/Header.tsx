import { User } from '@consta/uikit/User';
import { Text } from '@consta/uikit/Text';

import styles from './Header.module.css';

export const Header = () => {
  return (
    <header className={styles.header}>
      <div className={styles.titleContainer}>
        <Text size="l">Компьютерный тренажёрный комплекс</Text>
        <Text size="l" view="secondary">
          ЭЛОУ-АВТ
        </Text>
      </div>
      <User name="Демо-профиль" info="Обучаемый" size="l" />
    </header>
  );
};

Header.displayName = 'Header';
