import { Text } from '@consta/uikit/Text';
import styles from './ScenarioInfoItem.module.css';
import { Badge } from '@consta/uikit/Badge';

interface Props {
  title: string;
  description?: string;
  descriptionWithStatus?: boolean;
  descriptionList?: boolean;
  descriptionSelectedItems?: boolean;
  icon: string;
}

export const ScenarioInfoItem = (props: Props) => {
  const {
    title,
    description,
    descriptionWithStatus,
    descriptionList,
    descriptionSelectedItems,
    icon,
  } = props;

  return (
    <div className={styles.container}>
      <div className={styles.item}>
        <img src={icon} />
        <div className={styles.descriptionContainer}>
          <Text>{title}</Text>
          {description && <Text>{description}</Text>}
          {descriptionWithStatus && (
            <div>
              <div className={styles.badgeContainer}>
                <Badge form="round" status="success" />
                <Text>Устойчивый технологический режим</Text>
              </div>
              <Text>Н-1, Н-1А и Н-1В работают. Н-1Б остановлен</Text>
              <Text>Активных предупреждений нет</Text>
            </div>
          )}
          {descriptionList && (
            <div className={styles.listContainer}>
              <div className={styles.listItem}>
                <img />
                <Text>Корректность решений</Text>
              </div>
              <div className={styles.listItem}>
                <img />
                <Text>Время реакции</Text>
              </div>
              <div className={styles.listItem}>
                <img />
                <Text>Безопасность действий</Text>
              </div>
            </div>
          )}

          {descriptionSelectedItems && <div> </div>}
        </div>
      </div>
    </div>
  );
};

ScenarioInfoItem.displayName = 'ScenarioInfoItem';
