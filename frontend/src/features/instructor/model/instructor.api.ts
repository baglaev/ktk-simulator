import { apiInstructor } from '@/shared/api/baseApiConfig';

import type { InstructorResultsResponse } from './instructor.types';

export const instructorApi = {
  getResults: () => apiInstructor.get<InstructorResultsResponse>('/results'),
};
