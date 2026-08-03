import { IdentifiedFaults } from '@/features/identified-faults/Identified-faults/ui/IdentifiedFaults';
import { MainLayout } from '@/widgets/layouts/MainLayout/ui/MainLayout';
import { Text } from '@consta/uikit/Text';

import styles from './MainPage.module.css';

export const MainPage = () => {
  return (
    <main className={styles.main}>
      <MainLayout>
        <Text size="xl" className={styles.title}>
          Доступные сценарии
        </Text>
        <Text view="secondary">Выберите сценарий для прохождения тренировки</Text>
        <IdentifiedFaults />
      </MainLayout>
    </main>
  );
};

MainPage.displayName = 'MainPage';
