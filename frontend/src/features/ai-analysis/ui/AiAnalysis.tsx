import { observer } from 'mobx-react-lite';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { IconArrowDown } from '@consta/icons/IconArrowDown';
import { Text } from '@consta/uikit/Text';
import { Badge } from '@consta/uikit/Badge';
import { Button } from '@consta/uikit/Button';

import { IconWarning } from '@consta/icons/IconWarning';
import { IconCheck } from '@consta/icons/IconCheck';

import { HeaderSimulator } from '@/widgets/HeaderSimulator/ui/HeaderSimulator';

import { aiAnalysisStore } from '../model/aiAnalysis.store';

import styles from './AiAnalysis.module.css';

export const AiAnalysis = observer(() => {
  const navigate = useNavigate();

  const { analysis } = aiAnalysisStore;

  const [openedErrorCode, setOpenedErrorCode] = useState<string | null>(null);

  if (!analysis) {
    return (
      <section className={styles.section}>
        <Text>ИИ-разбор не загружен</Text>

        <Button
          label="Вернуться к результатам"
          view="secondary"
          onClick={() => navigate('/summary-results')}
        />
      </section>
    );
  }

  const isPassed = analysis.resultStatus === 'passed';

  return (
    <section className={styles.section}>
      <HeaderSimulator
        pageName="ИИ-разбор"
        descriptionPage="Раннее выявление неисправности сырьевого насоса группы Н-1"
        summaryEnabled
      />

      <div className={styles.titleContainer}>
        {isPassed ? <IconCheck size="l" view="success" /> : <IconWarning size="l" view="alert" />}

        <div>
          <Text size="2xl" weight="semibold" view={isPassed ? 'success' : 'alert'}>
            {isPassed ? 'Сценарий пройден' : 'Разбор ошибок прохождения'}
          </Text>

          <Text view="secondary">Анализ действий пользователя</Text>
        </div>
      </div>

      <div className={styles.summaryGrid}>
        <div className={styles.scoreCard}>
          <Text view="secondary">Итоговая оценка</Text>

          <Text size="3xl" weight="semibold">
            {analysis.totalScore}
            <span className={styles.scoreMax}>/100</span>
          </Text>
        </div>

        <div className={styles.summaryCard}>
          <Text weight="semibold" size="l">
            Краткий итог
          </Text>

          <Text>{analysis.summary}</Text>
        </div>
      </div>

      {analysis.strengths.length > 0 && (
        <section className={styles.card}>
          <Text size="l" weight="semibold">
            Сильные стороны
          </Text>

          <div className={styles.list}>
            {analysis.strengths.map((strength, index) => (
              <div key={`${strength}-${index}`} className={styles.listItem}>
                <Badge form="round" status="success" size="xs" />

                <Text>{strength}</Text>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className={styles.card}>
        <Text size="l" weight="semibold">
          Разбор ошибок
        </Text>

        <div className={styles.errors}>
          <div className={styles.errors}>
            {analysis.errors.map((error) => {
              const isOpen = openedErrorCode === error.code;

              return (
                <div key={error.code} className={styles.errorCard}>
                  <button
                    type="button"
                    className={styles.errorHeaderButton}
                    onClick={() => setOpenedErrorCode(isOpen ? null : error.code)}
                  >
                    <div className={styles.errorTitle}>
                      <Badge
                        form="round"
                        size="xs"
                        status={error.status === 'alert' ? 'error' : 'warning'}
                      />

                      <Text weight="semibold">
                        {error.order}. {error.userAction}
                      </Text>
                    </div>

                    <div className={styles.errorHeaderRight}>
                      <Badge label={error.classification} view="stroked" />

                      <IconArrowDown
                        size="s"
                        className={isOpen ? styles.arrowOpened : styles.arrow}
                      />
                    </div>
                  </button>

                  {isOpen && (
                    <div className={styles.errorDetails}>
                      <div className={styles.detailItem}>
                        <Text size="xs" view="secondary">
                          Последствие
                        </Text>

                        <Text size="s">{error.consequence}</Text>
                      </div>

                      <div className={styles.detailItem}>
                        <Text size="xs" view="secondary">
                          Как правильно
                        </Text>

                        <Text size="s">{error.correctApproach}</Text>
                      </div>

                      <div className={styles.detailItem}>
                        <Text size="xs" view="secondary">
                          При повторении
                        </Text>

                        <Text size="s">{error.prediction}</Text>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className={styles.card}>
        <Text size="l" weight="semibold">
          Рекомендации
        </Text>

        <div className={styles.list}>
          {analysis.recommendations.map((recommendation, index) => (
            <div key={`${recommendation}-${index}`} className={styles.recommendation}>
              <div className={styles.recommendationNumber}>{index + 1}</div>

              <Text>{recommendation}</Text>
            </div>
          ))}
        </div>
      </section>

      <div className={styles.buttons}>
        <Button
          label="Назад к результатам"
          view="secondary"
          size="l"
          onClick={() => navigate('/summary-results')}
        />

        <Button label="Повторить сценарий" size="l" onClick={() => navigate('/preparation')} />
      </div>
    </section>
  );
});

AiAnalysis.displayName = 'AiAnalysis';
