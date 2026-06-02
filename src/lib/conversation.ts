import type { ConversationScenario } from '@/src/lib/api/types';

export type ConversationScenarioCard = {
  id: ConversationScenario;
  icon: string;
  title: string;
  description: string;
};

export const conversationScenarios: ConversationScenarioCard[] = [
  {
    id: 'job_interview',
    icon: '💼',
    title: 'Job Interview',
    description: 'Practice confident introductions, experience, and common interview answers.',
  },
  {
    id: 'client_meeting',
    icon: '🤝',
    title: 'Client Meeting',
    description: 'Explain work clearly, ask questions, and sound professional with clients.',
  },
  {
    id: 'daily_conversation',
    icon: '☀️',
    title: 'Daily Conversation',
    description: 'Build simple natural English for everyday life and friendly small talk.',
  },
  {
    id: 'ordering_food',
    icon: '🍽️',
    title: 'Ordering Food',
    description: 'Practice polite restaurant English, requests, and simple follow-up questions.',
  },
  {
    id: 'travel_airport',
    icon: '✈️',
    title: 'Travel / Airport',
    description: 'Use practical English for check-in, directions, and travel support.',
  },
  {
    id: 'introduce_yourself',
    icon: '🙋',
    title: 'Introduce Yourself',
    description: 'Learn to introduce yourself naturally in short and clear sentences.',
  },
  {
    id: 'confidence_practice',
    icon: '🗣️',
    title: 'Confidence Practice',
    description: 'Practice speaking with stronger confidence and complete sentences.',
  },
];
