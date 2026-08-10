import { Text } from '@consta/uikit/Text';
import { ScenarioItem } from '../../ScenarioItem/ui/ScenarioItem';

import styles from './OtherScenarios.module.css';

export const OtherScenarios = () => {
  return (
    <section className={styles.container}>
      <Text size="l">Другие сценарии</Text>

      <div className={styles.scenariosContainer}>
        <ScenarioItem
          title="Пуск установки"
          description="Штатный сценарий"
          badgeName="В разработке"
          imageIcon="../../../../../public/pusk-ust.png"
        />
        <ScenarioItem
          title="Нарушение установки электродегидратора"
          description="Нештатный сценарий"
          badgeName="В разработке"
          imageIcon="../../../../../public/electro.png"
        />
        <ScenarioItem
          title="Отказ регулятора Е-15"
          description="Нештатный сценарий"
          badgeName="В разработке"
          imageIcon="../../../../../public/e-15.png"
        />
      </div>
    </section>
  );
};

OtherScenarios.displayName = 'OtherScenarios';
