import { Redirect } from 'expo-router';

export default function AppIndexRedirect() {
  return <Redirect href="/(app)/(tabs)" />;
}
