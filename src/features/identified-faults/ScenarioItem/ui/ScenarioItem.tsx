import { Badge } from '@consta/uikit/Badge';

import styles from './ScenarioItem.module.css';
import { Text } from '@consta/uikit/Text';

interface Props {
  title: string;
  description: string;
  badgeName: string;
  imageIcon: string;
}

export const ScenarioItem = (props: Props) => {
  const { title, description, badgeName, imageIcon } = props;

  return (
    <div className={styles.scenarioItem}>
      <Badge label={badgeName} status="disabled" />
      <div className={styles.container}>
        <img className={styles.imageItem} src={imageIcon}></img>
        <Text className={styles.titleItem} size="l">
          {title}
        </Text>
        <Text className={styles.descriptionItem} view="secondary">
          {description}
        </Text>
      </div>
    </div>
  );
};

ScenarioItem.displayName = 'ScenarioItem';
