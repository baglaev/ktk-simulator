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
          imageIcon="../../../../../public/main-1.jpg"
        />
        <ScenarioItem
          title="Нарушение установки электродегидратора"
          description="Нештатный сценарий"
          badgeName="В разработке"
          imageIcon="../../../../../public/main-2.jpg"
        />
        <ScenarioItem
          title="Отказ регулятора Е-15"
          description="Нештатный сценарий"
          badgeName="В разработке"
          imageIcon="../../../../../public/main-3.jpg"
        />
      </div>
    </section>
  );
};

OtherScenarios.displayName = 'OtherScenarios';
