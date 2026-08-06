import { MainLayout } from '@/widgets/layouts/MainLayout/ui/MainLayout';
import styles from './ScenarioPreparation.module.css';
import { ScenarioSection } from '@/features/scenario-section/ScenarioSection/ui/ScenarioSection';
import { Button } from '@consta/uikit/Button';
import { IconForward } from '@consta/icons/IconForward';
import { IconBackward } from '@consta/icons/IconBackward';

export const ScenarioPreparationPage = () => {
  return (
    <section className={styles.section}>
      <MainLayout>
        <ScenarioSection />
      </MainLayout>

      <div className={styles.buttonContaier}>
        <Button
          label="Назад"
          iconLeft={IconBackward}
          className={styles.nextButton}
          view="secondary"
          size="l"
        />

        <Button
          label="Начать сценарий"
          iconRight={IconForward}
          className={styles.nextButton}
          size="l"
        />
      </div>
    </section>
  );
};

ScenarioPreparationPage.displayName = 'ScenarioPreparationPage';
