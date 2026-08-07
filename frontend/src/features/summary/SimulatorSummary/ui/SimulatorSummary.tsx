import { HeaderSimulator } from '@/widgets/HeaderSimulator/ui/HeaderSimulator';
import { Text } from '@consta/uikit/Text';
import styles from './SimulatorSummary.module.css';
import { IconCheck } from '@consta/icons/IconCheck';
import { SummaryPoints } from './SummaryPoints';
import { TasksDoneContainer } from './TasksDoneContainer';
import { ParametrsControlled } from './ParametrsControlled';

export const SimulatorSummary = () => {
  return (
    <section className={styles.section}>
      <HeaderSimulator
        pageName="Результаты"
        descriptionPage="Раннее выявление неисправности сырьевого насоса группы Н-1"
        summaryEnabled
      />
      <div className={styles.titleContainer}>
        <IconCheck size="l" view="warning" />
        <Text size="2xl" className={styles.title} view="warning">
          Пройден с замечанями
        </Text>
      </div>
      <div className={styles.summaryPoints}>
        <SummaryPoints />
      </div>
      <div className={styles.columnsSection}>
        <TasksDoneContainer />
        <ParametrsControlled />
      </div>
    </section>
  );
};

SimulatorSummary.displayName = 'SimulatorSummary';
