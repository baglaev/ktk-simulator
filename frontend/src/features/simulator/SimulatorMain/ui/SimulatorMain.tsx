import { useEffect } from 'react';
import { observer } from 'mobx-react-lite';

import { HeaderSimulator } from '@/widgets/HeaderSimulator/ui/HeaderSimulator';
import { SimulatorEventLog } from '../../SimulatorEventLog/ui/SimulatorEventLog';
import { SimulatorInfoPanel } from '../../SimulatorInfoPanel/ui/SimulatorInfoPanel';
import { SimulatorSchema } from '../../SimulatorSchema/ui/SimulatorSchema';

import { scenarioStore } from '@/pages/ScenarioPreparation/model/scenario.store';
import { simulatorStore } from '../../SimulatorSchema/model/simulatorSchema.store';

import styles from './SimulatorMain.module.css';

export const SimulatorMain = observer(() => {
  const { sessionId } = scenarioStore;
  const { connect, disconnect } = simulatorStore;

  useEffect(() => {
    if (!sessionId) {
      return;
    }

    connect(sessionId);

    return () => {
      disconnect();
    };
  }, [sessionId, connect, disconnect]);

  return (
    <section className={styles.simulatorMain}>
      <HeaderSimulator
        pageName="Тренажёр"
        descriptionPage="Раннее выявленные неисправности сырьевого насоса группы Н-1"
        simulatorEnabled
      />

      <div className={styles.simulatorSchemaContainer}>
        <SimulatorSchema />
        <SimulatorInfoPanel />
      </div>

      <SimulatorEventLog />
    </section>
  );
});

SimulatorMain.displayName = 'SimulatorMain';
