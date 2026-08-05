import { IconAlert } from '@consta/icons/IconAlert';
import styles from './WarningInfo.module.css';
import { Text } from '@consta/uikit/Text';

export const WarningInfo = () => {
  return (
    <section className={styles.container}>
      <IconAlert />
      <Text>
        Демонстрационная учебная модель. Значения и динамиков параметров смоделированы. Не является
        производственной инструкцией.
      </Text>
    </section>
  );
};

WarningInfo.displayName = 'WarningInfo';
