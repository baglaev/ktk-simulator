import { Text } from '@consta/uikit/Text';
import { ScenarioItem } from '../../ScenarioItem/ui/ScenarioItem';

import styles from './OtherScenarios.module.css';

export const OtherScenarios = () => {
  return (
    <section>
      <Text size="l">Другие сценарии</Text>

      <div className={styles.scenariosContainer}>
        <ScenarioItem
          title="Пуск установки"
          description="Штатный сценарий"
          badgeName="В разработке"
          imageIcon="1"
        />
        <ScenarioItem
          title="Нарушение установки электродегидратора"
          description="Нештатный сценарий"
          badgeName="В разработке"
          imageIcon="2"
        />
        <ScenarioItem
          title="Отказ регулятора Е-15"
          description="Нештатный сценарий"
          badgeName="В разработке"
          imageIcon="3"
        />
      </div>
    </section>
  );
};

OtherScenarios.displayName = 'OtherScenarios';
