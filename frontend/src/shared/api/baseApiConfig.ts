import axios from 'axios';

export const { VITE_BASE_API } = import.meta.env;
export const { VITE_BASE_WS } = import.meta.env;

const baseApiConfig = (endPoint: string) => {
  return axios.create({
    baseURL: `${VITE_BASE_API}${endPoint}`,
    // withCredentials: true,
    headers: {
      'Content-Type': 'application/json',
    },
  });
};

export const apiSessions = baseApiConfig('/sessions');
export const apiScenarios = baseApiConfig('/scenarios');
export const apiInstructor = baseApiConfig('/instructor');
