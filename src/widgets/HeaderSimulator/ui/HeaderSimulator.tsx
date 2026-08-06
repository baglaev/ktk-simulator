import { Text } from '@consta/uikit/Text';
import styles from './HeaderSimulator.module.css';
import { IconWatchStroked } from '@consta/icons/IconWatchStroked';
import { Badge } from '@consta/uikit/Badge';
import { Button } from '@consta/uikit/Button';
import { User } from '@consta/uikit/User';

interface Props {
  pageName: string;
  descriptionPage: string;
  simulatorEnabled?: boolean;
  summaryEnabled?: boolean;
}

export const HeaderSimulator = (props: Props) => {
  const { pageName, descriptionPage, simulatorEnabled, summaryEnabled } = props;

  return (
    <header className={styles.header}>
      <div className={styles.titleContainer}>
        <Text>КТК ЭЛОУ-АВТ</Text>
        <Text>{pageName}</Text>
        <Text>{descriptionPage}</Text>
      </div>
      {simulatorEnabled && (
        <div className={styles.simulatorSection}>
          <div className={styles.timeContainer}>
            <IconWatchStroked />
            <Text>00:03</Text>
          </div>
          <Badge title="Обучающий режим" view="stroked" status="disabled" />
          <div className={styles.statusContainer}>
            <Badge form="round" status="success" size="xs" />
            <Text>Сценарий активен</Text>
          </div>
          <Button label="Завершить сценарий" form="round" />
        </div>
      )}

      {summaryEnabled && (
        <div className={styles.summarySection}>
          <Badge title="Обучающий режим" view="stroked" status="disabled" />
          <User name="Демо-профиль" info="Обучаемый" size="l" />
        </div>
      )}
    </header>
  );
};

HeaderSimulator.displayName = 'HeaderSimulator';
