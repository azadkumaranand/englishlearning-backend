import { env } from '@/src/lib/env';

type RequestOptions = RequestInit & {
  token?: string | null;
};

type StreamRequestOptions<TEvent> = Omit<RequestOptions, 'signal'> & {
  onEvent: (event: TEvent) => void;
  signal?: AbortSignal;
};

const REQUEST_TIMEOUT_MS = 60_000;

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

function buildHeaders(options: RequestOptions): HeadersInit {
  const isFormDataBody = typeof FormData !== 'undefined' && options.body instanceof FormData;
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(!isFormDataBody && options.body ? { 'Content-Type': 'application/json' } : {}),
  };

  if (options.headers) {
    Object.assign(headers, options.headers as Record<string, string>);
  }
  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  return headers;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  const timeoutPromise = new Promise<Response>((_, reject) => {
    timeoutId = setTimeout(() => {
      reject(
        new ApiError(
          `Request timed out after ${REQUEST_TIMEOUT_MS / 1000}s. Check the API server and EXPO_PUBLIC_API_BASE_URL.`,
          0,
          null
        )
      );
    }, REQUEST_TIMEOUT_MS);
  });

  let response: Response;

  try {
    response = (await Promise.race([
      fetch(`${env.apiBaseUrl}${path}`, {
        ...options,
        headers: buildHeaders(options),
      }),
      timeoutPromise,
    ])) as Response;
  } catch (error) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      'Unable to reach the API server. Check the backend status and mobile API base URL.',
      0,
      null
    );
  }

  if (timeoutId) {
    clearTimeout(timeoutId);
  }

  const contentType = response.headers.get('content-type') ?? '';
  const data = contentType.includes('application/json')
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message =
      typeof data === 'object' && data !== null && 'detail' in data
        ? String((data as { detail: unknown }).detail)
        : response.statusText || 'Request failed';
    throw new ApiError(message, response.status, data);
  }

  return data as T;
}

export async function apiUploadRequest<T>(
  path: string,
  options: Omit<RequestOptions, 'body'> & { body: FormData }
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    const settleReject = (error: ApiError) => {
      xhr.onerror = null;
      xhr.onload = null;
      xhr.onabort = null;
      xhr.ontimeout = null;
      reject(error);
    };

    const settleResolve = (value: T) => {
      xhr.onerror = null;
      xhr.onload = null;
      xhr.onabort = null;
      xhr.ontimeout = null;
      resolve(value);
    };

    xhr.open(options.method ?? 'POST', `${env.apiBaseUrl}${path}`);
    xhr.timeout = REQUEST_TIMEOUT_MS;

    const headers = buildHeaders({ ...options, body: options.body });
    Object.entries(headers as Record<string, string>).forEach(([key, value]) => {
      xhr.setRequestHeader(key, value);
    });

    xhr.onload = () => {
      const responseText = xhr.responseText ?? '';
      const contentType = xhr.getResponseHeader('content-type') ?? '';
      let data: unknown = responseText;

      if (responseText.length > 0 && contentType.includes('application/json')) {
        try {
          data = JSON.parse(responseText);
        } catch {
          data = responseText;
        }
      }

      if (!xhr.status || xhr.status < 200 || xhr.status >= 300) {
        const message =
          typeof data === 'object' && data !== null && 'detail' in data
            ? String((data as { detail: unknown }).detail)
            : xhr.statusText || 'Request failed';
        settleReject(new ApiError(message, xhr.status || 0, data));
        return;
      }

      settleResolve(data as T);
    };

    xhr.onerror = () => {
      settleReject(
        new ApiError(
          'Unable to reach the API server. Check the backend status and mobile API base URL.',
          0,
          null
        )
      );
    };

    xhr.ontimeout = () => {
      settleReject(
        new ApiError(
          `Request timed out after ${REQUEST_TIMEOUT_MS / 1000}s. Check the API server and EXPO_PUBLIC_API_BASE_URL.`,
          0,
          null
        )
      );
    };

    xhr.onabort = () => {
      settleReject(new ApiError('Request was cancelled.', 0, null));
    };

    xhr.send(options.body);
  });
}

export async function apiStreamRequest<TEvent>(
  path: string,
  options: StreamRequestOptions<TEvent>
): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    let lastProcessedLength = 0;
    let buffer = '';
    let settled = false;
    let aborted = false;

    const cleanup = () => {
      if (options.signal) {
        options.signal.removeEventListener('abort', handleAbort);
      }
      xhr.onprogress = null;
      xhr.onerror = null;
      xhr.onload = null;
      xhr.onabort = null;
      xhr.ontimeout = null;
    };

    const settleResolve = () => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve();
    };

    const settleReject = (error: ApiError) => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(error);
    };

    const dispatchEventBlock = (block: string) => {
      const trimmedBlock = block.trim();
      if (!trimmedBlock) {
        return;
      }

      const dataLines = trimmedBlock
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).trim());

      const rawPayload = dataLines.length > 0 ? dataLines.join('\n') : trimmedBlock;
      if (!rawPayload || rawPayload === '[DONE]') {
        return;
      }

      try {
        options.onEvent(JSON.parse(rawPayload) as TEvent);
      } catch (error) {
        if (error instanceof ApiError) {
          settleReject(error);
          return;
        }
        settleReject(
          new ApiError('Received an invalid streamed response from the server.', 0, rawPayload)
        );
      }
    };

    const parseChunk = (chunk: string) => {
      buffer += chunk.replace(/\r\n/g, '\n');

      while (true) {
        const separatorIndex = buffer.indexOf('\n\n');
        if (separatorIndex === -1) {
          break;
        }

        const block = buffer.slice(0, separatorIndex);
        buffer = buffer.slice(separatorIndex + 2);
        dispatchEventBlock(block);
        if (settled) {
          return;
        }
      }
    };

    const flushResponseText = () => {
      const nextText = xhr.responseText.slice(lastProcessedLength);
      lastProcessedLength = xhr.responseText.length;
      if (nextText) {
        parseChunk(nextText);
      }
    };

    const handleAbort = () => {
      aborted = true;
      xhr.abort();
    };

    xhr.open(options.method ?? 'GET', `${env.apiBaseUrl}${path}`);
    xhr.timeout = REQUEST_TIMEOUT_MS;

    const headers = buildHeaders(options);
    Object.entries(headers as Record<string, string>).forEach(([key, value]) => {
      xhr.setRequestHeader(key, value);
    });

    xhr.onprogress = () => {
      flushResponseText();
    };

    xhr.onload = () => {
      flushResponseText();

      if (!xhr.status || xhr.status < 200 || xhr.status >= 300) {
        const text = xhr.responseText?.trim();
        let data: unknown = text;
        try {
          data = text ? JSON.parse(text) : null;
        } catch {
          data = text;
        }
        const message =
          typeof data === "object" && data !== null && "detail" in data
            ? String((data as { detail: unknown }).detail)
            : xhr.statusText || 'Request failed';
        settleReject(new ApiError(message, xhr.status || 0, data));
        return;
      }

      if (buffer.trim().length > 0) {
        dispatchEventBlock(buffer);
        if (settled) {
          return;
        }
      }

      settleResolve();
    };

    xhr.onerror = () => {
      settleReject(
        new ApiError(
          'Unable to reach the API server. Check the backend status and mobile API base URL.',
          0,
          null
        )
      );
    };

    xhr.ontimeout = () => {
      settleReject(
        new ApiError(
          `Request timed out after ${REQUEST_TIMEOUT_MS / 1000}s. Check the API server and EXPO_PUBLIC_API_BASE_URL.`,
          0,
          null
        )
      );
    };

    xhr.onabort = () => {
      if (aborted) {
        settleReject(new ApiError('Request was cancelled.', 0, null));
        return;
      }
      settleReject(new ApiError('The streamed request was interrupted.', 0, null));
    };

    if (options.signal) {
      if (options.signal.aborted) {
        handleAbort();
        return;
      }
      options.signal.addEventListener('abort', handleAbort);
    }

    try {
      xhr.send((options.body as XMLHttpRequestBodyInit | null | undefined) ?? null);
    } catch {
      settleReject(
        new ApiError(
          'Unable to reach the API server. Check the backend status and mobile API base URL.',
          0,
          null
        )
      );
    }
  });
}
