import { Text } from '@consta/uikit/Text';
import styles from './HeaderSimulator.module.css';
import { IconWatchStroked } from '@consta/icons/IconWatchStroked';
import { Badge } from '@consta/uikit/Badge';
import { Button } from '@consta/uikit/Button';
import { User } from '@consta/uikit/User';
import { observer } from 'mobx-react-lite';
import { simulatorStore } from '@/features/simulator/SimulatorSchema/model/simulatorSchema.store';
import { useNavigate } from 'react-router-dom';
import { authStore } from '@/features/auth/model/auth.api.store';
import { IconExit } from '@consta/icons/IconExit';

interface Props {
  pageName: string;
  descriptionPage: string;
  simulatorEnabled?: boolean;
  summaryEnabled?: boolean;
}

export const HeaderSimulator = observer((props: Props) => {
  const { pageName, descriptionPage, simulatorEnabled, summaryEnabled } = props;

  const { formattedElapsedTime } = simulatorStore;

  const navigate = useNavigate();

  const handleLogout = () => {
    authStore.logout();

    navigate('/login', {
      replace: true,
    });
  };

  return (
    <header className={styles.header}>
      <div className={styles.titleContainer}>
        <Text size="l">КТК ЭЛОУ-АВТ</Text>
        <Text size="l">{pageName}</Text>
        <Text size="l">{descriptionPage}</Text>
      </div>
      {simulatorEnabled && (
        <div className={styles.simulatorSection}>
          <div className={styles.timeContainer}>
            <IconWatchStroked />
            <Text>{formattedElapsedTime}</Text>
          </div>
          <Badge title="Обучающий режим" view="stroked" status="disabled" />
          <div className={styles.statusContainer}>
            <Badge form="round" status="success" size="xs" />
            <Text>Сценарий активен</Text>
          </div>
          <Button label="Завершить сценарий" view="secondary" />
        </div>
      )}

      {summaryEnabled && (
        <div className={styles.summarySection}>
          <Badge label="Обучающий режим" view="stroked" size="l" />

          <div className={styles.userContainer}>
            <User name="Демо-профиль" info="Обучаемый" size="l" />
            <Button onlyIcon view="ghost" iconLeft={IconExit} onClick={handleLogout} />
          </div>
        </div>
      )}
    </header>
  );
});

HeaderSimulator.displayName = 'HeaderSimulator';
