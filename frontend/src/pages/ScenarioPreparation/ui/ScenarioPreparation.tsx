import { MainLayout } from '@/widgets/layouts/MainLayout/ui/MainLayout';
import styles from './ScenarioPreparation.module.css';
import { ScenarioSection } from '@/features/scenario-section/ScenarioSection/ui/ScenarioSection';
import { Button } from '@consta/uikit/Button';
import { IconForward } from '@consta/icons/IconForward';
import { IconBackward } from '@consta/icons/IconBackward';
import { useEffect } from 'react';
import { scenarioStore } from '../model/scenario.store';
import { observer } from 'mobx-react-lite';
import { useNavigate } from 'react-router-dom';

export const ScenarioPreparationPage = observer(() => {
  const { isStarting, isLoading, initialize, startScenario } = scenarioStore;

  const navigate = useNavigate();

  useEffect(() => {
    initialize();
  }, [initialize]);

  const handleStartScenario = async () => {
    try {
      await startScenario();

      navigate('/simulator');
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <section className={styles.container}>
      <MainLayout>
        <div>
          <ScenarioSection />

          <div className={styles.buttonContaier}>
            <Button
              label="Назад"
              iconLeft={IconBackward}
              className={styles.nextButton}
              view="secondary"
              size="l"
              onClick={() => navigate('/')}
            />

            <Button
              label="Начать сценарий"
              iconRight={IconForward}
              className={styles.nextButton}
              size="l"
              onClick={handleStartScenario}
              loading={isStarting}
              disabled={isLoading || isStarting}
            />
          </div>
        </div>
      </MainLayout>
    </section>
  );
});

ScenarioPreparationPage.displayName = 'ScenarioPreparationPage';
