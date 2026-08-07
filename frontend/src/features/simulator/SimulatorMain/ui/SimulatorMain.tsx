import { HeaderSimulator } from '@/widgets/HeaderSimulator/ui/HeaderSimulator';
import { SimulatorEventLog } from '../../SimulatorEventLog/ui/SimulatorEventLog';
import { SimulatorInfoPanel } from '../../SimulatorInfoPanel/ui/SimulatorInfoPanel';
import { SimulatorSchema } from '../../SimulatorSchema/ui/SimulatorSchema';
import styles from './SimulatorMain.module.css';

export const SimulatorMain = () => {
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
};

SimulatorMain.displayName = 'SimulatorMain';
