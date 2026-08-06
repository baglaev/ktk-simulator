import { Text } from '@consta/uikit/Text';
import styles from './ScenarioInfoItem.module.css';
import { Badge } from '@consta/uikit/Badge';
import { Radio } from '@consta/uikit/Radio';
import { IconCheck } from '@consta/icons/IconCheck';

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
          <Text size="l">{title}</Text>
          {description && <Text className={styles.description}>{description}</Text>}
          {descriptionWithStatus && (
            <div className={styles.statusContainer}>
              <div className={styles.badgeContainer}>
                <Badge form="round" status="success" size="xs" />
                <Text>Устойчивый технологический режим</Text>
              </div>
              <Text>Н-1, Н-1А и Н-1В работают. Н-1Б остановлен</Text>
              <Text>Активных предупреждений нет</Text>
            </div>
          )}
          {descriptionList && (
            <div className={styles.listContainer}>
              <div className={styles.listItem}>
                <IconCheck size="s" />
                <Text>Корректность решений</Text>
              </div>
              <div className={styles.listItem}>
                <IconCheck size="s" />
                <Text>Время реакции</Text>
              </div>
              <div className={styles.listItem}>
                <IconCheck size="s" />
                <Text>Безопасность действий</Text>
              </div>
            </div>
          )}

          {descriptionSelectedItems && (
            <div>
              <div className={styles.radioContainer}>
                <Radio label="Обучающий" />
                <Text className={styles.radioText} view="secondary">
                  Проактивные ИИ-подсказки во время прохождения
                </Text>
              </div>
              <div className={styles.radioContainer}>
                <Radio label="Контрольный" />
                <Text className={styles.radioText} view="secondary">
                  Прохождение без ИИ-подсказок
                </Text>
              </div>

              <Text view="secondary" size="s" className={styles.textSelectDescription}>
                Итоговая оценка и ИИ-разбор доступны в обоих режимах
              </Text>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

ScenarioInfoItem.displayName = 'ScenarioInfoItem';
