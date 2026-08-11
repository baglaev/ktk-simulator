import { useState } from 'react';
import { observer } from 'mobx-react-lite';
import { useNavigate } from 'react-router-dom';
import { scenarioStore } from '@/pages/ScenarioPreparation/model/scenario.store';
import { Text } from '@consta/uikit/Text';
import { Badge } from '@consta/uikit/Badge';
import { Button } from '@consta/uikit/Button';

import { IconWarning } from '@consta/icons/IconWarning';
import { IconCheck } from '@consta/icons/IconCheck';
import { IconArrowDown } from '@consta/icons/IconArrowDown';

import { HeaderSimulator } from '@/widgets/HeaderSimulator/ui/HeaderSimulator';

import { aiAnalysisStore } from '../model/aiAnalysis.store';

import styles from './AiAnalysis.module.css';

export const AiAnalysis = observer(() => {
  const navigate = useNavigate();

  const [openedErrorCode, setOpenedErrorCode] = useState<string | null>(null);

  const { analysis } = aiAnalysisStore;

  const handleDownloadReport = async () => {
    if (!scenarioStore.sessionId) {
      console.error('sessionId отсутствует');
      return;
    }

    try {
      await aiAnalysisStore.downloadReport(scenarioStore.sessionId);
    } catch (error) {
      console.error(error);
    }
  };

  if (!analysis) {
    return (
      <section className={styles.section}>
        <Text size="l">ИИ-разбор не загружен</Text>

        <Button
          label="Вернуться к результатам"
          view="secondary"
          onClick={() => navigate('/summary-results')}
        />
      </section>
    );
  }

  const isFailed = analysis.resultStatus === 'failed';
  const resultTitle = isFailed
    ? 'Разбор ошибок прохождения'
    : analysis.resultStatus === 'passed_with_remarks'
      ? 'Сценарий пройден с замечаниями'
      : 'Сценарий пройден';

  return (
    <section className={styles.section}>
      <HeaderSimulator
        pageName="ИИ-разбор"
        descriptionPage="Раннее выявление неисправности сырьевого насоса группы Н-1"
        summaryEnabled
      />

      <div className={styles.content}>
        <div className={styles.titleContainer}>
          {isFailed ? <IconWarning size="l" view="alert" /> : <IconCheck size="l" view="success" />}

          <div className={styles.titleText}>
            <Text size="2xl" weight="semibold" view={isFailed ? 'alert' : 'success'}>
              {resultTitle}
            </Text>

            <Text size="s" view="secondary">
              Анализ действий пользователя по результатам сценария
            </Text>
          </div>
        </div>

        <div className={styles.summaryGrid}>
          <div className={styles.scoreCard}>
            <Text size="s" view="secondary">
              Итоговая оценка
            </Text>

            <Text size="3xl" weight="semibold">
              {analysis.totalScore}

              <span className={styles.scoreMax}>/100</span>
            </Text>
          </div>

          <div className={styles.summaryCard}>
            <Text size="l" weight="semibold">
              Краткий итог
            </Text>

            <Text size="s">{analysis.summary}</Text>
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

                  <Text size="s">{strength}</Text>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className={styles.card}>
          <div className={styles.sectionTitle}>
            <Text size="l" weight="semibold">
              Разбор ошибок
            </Text>

            <Text size="xs" view="secondary">
              {analysis.errors.length}
            </Text>
          </div>

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

                      <Text size="s" weight="semibold" className={styles.errorTitleText}>
                        {error.order}. {error.userAction}
                      </Text>
                    </div>

                    <div className={styles.errorHeaderRight}>
                      <Badge size="xs" label={error.classification} view="stroked" />

                      <IconArrowDown
                        size="xs"
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

                        <Text size="xs">{error.consequence}</Text>
                      </div>

                      <div className={styles.detailItem}>
                        <Text size="xs" view="secondary">
                          Как правильно
                        </Text>

                        <Text size="xs">{error.correctApproach}</Text>
                      </div>

                      <div className={styles.detailItem}>
                        <Text size="xs" view="secondary">
                          При повторении
                        </Text>

                        <Text size="xs">{error.prediction}</Text>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        <section className={styles.card}>
          <Text size="l" weight="semibold">
            Рекомендации
          </Text>

          <div className={styles.recommendations}>
            {analysis.recommendations.map((recommendation, index) => (
              <div key={`${recommendation}-${index}`} className={styles.recommendation}>
                <div className={styles.recommendationNumber}>{index + 1}</div>

                <Text size="s">{recommendation}</Text>
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

          <Button
            label="Скачать PDF"
            view="secondary"
            size="l"
            loading={aiAnalysisStore.isReportLoading}
            disabled={aiAnalysisStore.isReportLoading}
            onClick={handleDownloadReport}
          />

          <Button label="Повторить сценарий" size="l" onClick={() => navigate('/preparation')} />
        </div>
      </div>
    </section>
  );
});

AiAnalysis.displayName = 'AiAnalysis';
