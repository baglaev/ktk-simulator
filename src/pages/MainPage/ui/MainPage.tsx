import { IdentifiedFaults } from '@/features/identified-faults/Identified-faults/ui/IdentifiedFaults';
import { MainLayout } from '@/widgets/layouts/MainLayout/ui/MainLayout';
import { Text } from '@consta/uikit/Text';

import styles from './MainPage.module.css';
import { OtherScenarios } from '@/features/identified-faults/OtherScenarios/ui/OtherScenarios';

export const MainPage = () => {
  return (
    <main className={styles.main}>
      <MainLayout>
        <Text size="xl" className={styles.title}>
          Доступные сценарии
        </Text>
        <Text className={styles.description} view="secondary">
          Выберите сценарий для прохождения тренировки
        </Text>
        <IdentifiedFaults />
        <OtherScenarios />
      </MainLayout>
    </main>
  );
};

MainPage.displayName = 'MainPage';
