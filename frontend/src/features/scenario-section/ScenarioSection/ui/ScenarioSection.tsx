import { Text } from '@consta/uikit/Text';
import { Badge } from '@consta/uikit/Badge';
import { IconDocFilled } from '@consta/icons/IconDocFilled';
import { IconDebug } from '@consta/icons/IconDebug';
import { IconAddToComparison } from '@consta/icons/IconAddToComparison';
import styles from './ScenarioSection.module.css';

import { ScenarioInfoItem } from '../../ScenarioInfoItem/ui/ScenarioInfoItem';

export const ScenarioSection = () => {
  return (
    <section>
      <Text size="2xl" className={styles.title}>
        Подготовка к сценарию
      </Text>
      <div className={styles.descriptionSection}>
        <Badge size="l" label="Демо" />
        <div className={styles.descriptionContainer}>
          <Text className={styles.description} size="l">
            Раннее выявление неисправности сырьевого насоса группы Н-1
          </Text>
          <div className={styles.descriptionIconSection}>
            <div className={styles.descriptionIconContainer}>
              <IconDocFilled />
              <Text size="s">Нештатный диагностический</Text>
            </div>
            <div className={styles.descriptionIconContainer}>
              <IconDebug />
              <Text size="s">~ 3 минуты</Text>
            </div>
            <div className={styles.descriptionIconContainer}>
              <IconAddToComparison />
              <Text size="s">Средняя</Text>
            </div>
          </div>
        </div>
      </div>

      <div className={styles.scenariosContainer}>
        <ScenarioInfoItem
          title="Учебная задача"
          description="Выявить неисправный насос и предотвратить снижение уровня Е-15"
          icon="1"
        />
        <ScenarioInfoItem title="Исходное состояние" descriptionWithStatus icon="2" />
        <ScenarioInfoItem title="Что учитывается при оценке" descriptionList icon="3" />
        <ScenarioInfoItem title="Выберите режим" descriptionSelectedItems icon="4" />
      </div>
    </section>
  );
};

ScenarioSection.displayName = 'ScenarioSection';
