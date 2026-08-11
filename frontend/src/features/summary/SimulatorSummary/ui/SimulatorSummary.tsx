import { HeaderSimulator } from '@/widgets/HeaderSimulator/ui/HeaderSimulator';
import { Text } from '@consta/uikit/Text';
import styles from './SimulatorSummary.module.css';
import { IconCheck } from '@consta/icons/IconCheck';
import { SummaryPoints } from './SummaryPoints';
import { TasksDoneContainer } from './TasksDoneContainer';
import { ParametrsControlled } from './ParametrsControlled';
import { RecordedComments } from './RecordedComments';
import { Button } from '@consta/uikit/Button';
import { useNavigate } from 'react-router-dom';
import { observer } from 'mobx-react-lite';
import { resultStore } from '../../model/result.store';

export const SimulatorSummary = observer(() => {
  const navigate = useNavigate();

  const { result } = resultStore;

  if (!result) {
    return (
      <section className={styles.section}>
        <Text>Результат сценария не загружен</Text>
      </section>
    );
  }

  const isPassed = result.outcome === 'passed';

  return (
    <section className={styles.section}>
      <HeaderSimulator
        pageName="Результаты"
        descriptionPage="Раннее выявление неисправности сырьевого насоса группы Н-1"
        summaryEnabled
      />
      <div className={styles.titleContainer}>
        <IconCheck size="l" view={isPassed ? 'success' : 'alert'} />

        <div>
          <Text size="2xl" className={styles.title} view={isPassed ? 'success' : 'alert'}>
            {isPassed ? 'Сценарий пройден' : 'Сценарий не пройден'}
          </Text>

          <Text view="secondary">{result.summary}</Text>
        </div>
      </div>
      <div className={styles.summaryPoints}>
        <SummaryPoints
          totalScore={result.totalScore}
          maxScore={result.maxScore}
          elapsedTimeMs={result.elapsedTimeMs}
          mode={result.mode}
        />
      </div>
      <div className={styles.columnsSection}>
        <TasksDoneContainer tasks={result.taskExecution} />
        <ParametrsControlled parameters={result.controlledParameters} />
      </div>
      <RecordedComments remarks={result.remarks} />

      <div className={styles.buttonsContainer}>
        <Button label="На главную" view="secondary" size="l" onClick={() => navigate('/')} />
        <Button
          label="Повторить сценарий"
          view="secondary"
          size="l"
          onClick={() => navigate('/preparation')}
        />
        <Button label="Перейти к ИИ-разбору" size="l" />
      </div>
    </section>
  );
});

SimulatorSummary.displayName = 'SimulatorSummary';
