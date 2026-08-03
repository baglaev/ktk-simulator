import { Badge } from '@consta/uikit/Badge';
import { IconDocFilled } from '@consta/icons/IconDocFilled';
import { IconAddToComparison } from '@consta/icons/IconAddToComparison';
import { IconDebug } from '@consta/icons/IconDebug';
import { IconAlignLeft } from '@consta/icons/IconAlignLeft';
import { Button } from '@consta/uikit/Button';
import { IconForward } from '@consta/icons/IconForward';

import styles from './IdentifiedFaults.module.css';
import { Text } from '@consta/uikit/Text';

export const IdentifiedFaults = () => {
  return (
    <div className={styles.container}>
      <div className={styles.badges}>
        <Badge label="ДЕМО" />
        <Badge label="Доступен" status="success" />
      </div>
      <Text size="l">Раннее выявление неисправности насоса Н-1</Text>
      <div className={styles.previewContainer}>
        <div></div>
        <div>
          <div className={styles.previewStats}>
            <div className={styles.statItem}>
              <IconDocFilled className={styles.iconItem} size="l" />
              <Text view="secondary" className={styles.statTitle}>
                Тип сценария
              </Text>
              <Text className={styles.statValue}>Нештатный диагностический</Text>
            </div>
            <div className={styles.statItem}>
              <IconDebug className={styles.iconItem} size="l" />
              <Text view="secondary" className={styles.statTitle}>
                Длительность
              </Text>
              <Text className={styles.statValue}>~ 3 минуты</Text>
            </div>
            <div className={styles.statItem}>
              <IconAddToComparison className={styles.iconItem} size="l" />
              <Text view="secondary" className={styles.statTitle}>
                Сложность
              </Text>
              <Text className={styles.statValue}>Средняя</Text>
            </div>
            <div className={styles.statItem}>
              <IconAlignLeft className={styles.iconItem} size="l" />
              <Text view="secondary" className={styles.statTitle}>
                Режим
              </Text>
              <Text className={styles.statValue}>Обучающий-контрольный</Text>
            </div>
          </div>
          <Button
            label="Перейти к подготовке"
            iconRight={IconForward}
            className={styles.nextButton}
          />
        </div>
      </div>
    </div>
  );
};

IdentifiedFaults.displayName = 'IdentifiedFaults';
