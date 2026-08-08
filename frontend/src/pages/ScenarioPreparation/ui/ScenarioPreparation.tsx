// import { MainLayout } from '@/widgets/layouts/MainLayout/ui/MainLayout';
// import styles from './ScenarioPreparation.module.css';
// import { ScenarioSection } from '@/features/scenario-section/ScenarioSection/ui/ScenarioSection';
// import { Button } from '@consta/uikit/Button';
// import { IconForward } from '@consta/icons/IconForward';
// import { IconBackward } from '@consta/icons/IconBackward';
// import { useEffect } from 'react';
// import { scenarioStore } from '../model/scenario.store';
// import { observer } from 'mobx-react-lite';

// export const ScenarioPreparationPage = observer(() => {
//   const { scenarios, fetchAllScenarios } = scenarioStore;

//   console.log(scenarios);

//   useEffect(() => {
//     fetchAllScenarios();
//   }, [fetchAllScenarios]);

//   return (
//     <section className={styles.section}>
//       <MainLayout>
//         <ScenarioSection />
//       </MainLayout>

//       <div className={styles.buttonContaier}>
//         <Button
//           label="Назад"
//           iconLeft={IconBackward}
//           className={styles.nextButton}
//           view="secondary"
//           size="l"
//         />

//         <Button
//           label="Начать сценарий"
//           iconRight={IconForward}
//           className={styles.nextButton}
//           size="l"
//         />
//       </div>
//     </section>
//   );
// });

// ScenarioPreparationPage.displayName = 'ScenarioPreparationPage';

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
  const { selectedScenario, sessionId, isLoading, isStarting, initialize, startSession } =
    scenarioStore;

  const navigate = useNavigate();

  useEffect(() => {
    initialize();
  }, [initialize]);

  const handleStartScenario = async () => {
    try {
      await startSession();

      console.log('Сценарий запущен');

      // здесь потом переход на страницу симулятора
      navigate('/simulator');
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <MainLayout>
      <section className={styles.container}>
        {selectedScenario && <ScenarioSection />}

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
            onClick={handleStartScenario}
            loading={isStarting}
            disabled={!sessionId || isLoading}
          />
        </div>
      </section>
    </MainLayout>
  );
});

ScenarioPreparationPage.displayName = 'ScenarioPreparationPage';
