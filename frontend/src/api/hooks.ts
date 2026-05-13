
import {
  useMutation,
  useQuery,
  UseQueryResult,
  UseMutationResult,
} from "@tanstack/react-query";
import { chatAPI } from "./services";
import type {
  ChatRequestPayload,
  ChatResponse,
  SchemaInfo,
  SuggestedQueries,
  HealthCheck,
} from "@/types/api";
import { AxiosError } from "axios";

export const useSendMessage = (): UseMutationResult<
  ChatResponse,
  AxiosError,
  ChatRequestPayload,
  unknown
> => {
  return useMutation({
    mutationFn: (payload: ChatRequestPayload) => chatAPI.sendMessage(payload),
  });
};

export const useHealth = (): UseQueryResult<HealthCheck, AxiosError> => {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => chatAPI.getHealth(),
    staleTime: 1000 * 60,
  });
};

export const useSchema = (): UseQueryResult<SchemaInfo, AxiosError> => {
  return useQuery({
    queryKey: ["schema"],
    queryFn: () => chatAPI.getSchema(),
    staleTime: 1000 * 60 * 60,
  });
};

export const useSuggestedQueries = (): UseQueryResult<
  SuggestedQueries,
  AxiosError
> => {
  return useQuery({
    queryKey: ["suggestedQueries"],
    queryFn: () => chatAPI.getSuggestedQueries(),
    staleTime: 1000 * 60 * 60,
  });
};