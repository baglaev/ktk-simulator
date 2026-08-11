import { Text } from '@consta/uikit/Text';
import { observer } from 'mobx-react-lite';

import { simulatorStore } from '../../SimulatorSchema/model/simulatorSchema.store';

import styles from './SimulatorHint.module.css';

export const SimulatorHint = observer(() => {
  const { activeHint, dismissHint } = simulatorStore;

  if (!activeHint) {
    return null;
  }

  return (
    <aside
      className={`${styles.hint} ${styles[activeHint.level]}`}
      role="status"
      aria-live="polite"
    >
      <div className={styles.content}>
        <Text size="xs" view="secondary">
          Учебная подсказка
        </Text>
        <Text size="m" weight="semibold">
          {activeHint.title}
        </Text>
        <Text size="s">{activeHint.message}</Text>
      </div>

      <button
        className={styles.close}
        type="button"
        aria-label="Закрыть подсказку"
        onClick={dismissHint}
      >
        ×
      </button>
    </aside>
  );
});

SimulatorHint.displayName = 'SimulatorHint';
