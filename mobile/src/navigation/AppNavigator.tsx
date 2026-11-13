import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../theme/colors';
import { useAuth } from '../context/AuthContext';

import FeedScreen from '../screens/FeedScreen';
import AttendanceScreen from '../screens/AttendanceScreen';
import NoticesScreen from '../screens/NoticesScreen';
import CalendarScreen from '../screens/CalendarScreen';
import GalleryScreen from '../screens/GalleryScreen';
import ProfileScreen from '../screens/ProfileScreen';
import LoginScreen from '../screens/LoginScreen';
import AdministrationScreen from '../screens/AdministrationScreen';

const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator();

function MainTabs() {
  const { user } = useAuth();

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: Colors.primary,
        tabBarInactiveTintColor: Colors.textMuted,
        tabBarStyle: {
          backgroundColor: '#FFFFFF',
          borderTopColor: '#E2E8F0',
          height: 60,
          paddingBottom: 8,
          paddingTop: 6,
        },
        tabBarLabelStyle: {
          fontSize: 10,
          fontWeight: '600',
        },
        tabBarIcon: ({ color, size, focused }) => {
          let iconName: any = 'newspaper';
          if (route.name === 'FeedTab') {
            iconName = focused ? 'newspaper' : 'newspaper-outline';
          } else if (route.name === 'AttendanceTab') {
            iconName = focused ? 'calendar-number' : 'calendar-number-outline';
          } else if (route.name === 'NoticesTab') {
            iconName = focused ? 'notifications' : 'notifications-outline';
          } else if (route.name === 'CalendarTab') {
            iconName = focused ? 'calendar' : 'calendar-outline';
          } else if (route.name === 'AdminTab') {
            iconName = focused ? 'business' : 'business-outline';
          } else if (route.name === 'GalleryTab') {
            iconName = focused ? 'images' : 'images-outline';
          } else if (route.name === 'ProfileTab') {
            iconName = focused ? 'person' : 'person-outline';
          }
          return <Ionicons name={iconName} size={size} color={color} />;
        },
      })}
    >
      <Tab.Screen
        name="FeedTab"
        component={FeedScreen}
        options={{ tabBarLabel: 'न्युज फिड' }}
      />
      <Tab.Screen
        name="AttendanceTab"
        component={AttendanceScreen}
        options={{ tabBarLabel: 'हाजिरी' }}
      />
      <Tab.Screen
        name="NoticesTab"
        component={NoticesScreen}
        options={{ tabBarLabel: 'सूचना पाटी' }}
      />
      <Tab.Screen
        name="CalendarTab"
        component={CalendarScreen}
        options={{ tabBarLabel: 'क्यालेन्डर' }}
      />
      <Tab.Screen
        name="AdminTab"
        component={AdministrationScreen}
        options={{ tabBarLabel: 'प्रशासन' }}
      />
      <Tab.Screen
        name="GalleryTab"
        component={GalleryScreen}
        options={{ tabBarLabel: 'ग्यालरी' }}
      />
      <Tab.Screen
        name="ProfileTab"
        component={user ? ProfileScreen : LoginScreen}
        options={{ tabBarLabel: user ? 'प्रोफाइल' : 'लगइन' }}
      />
    </Tab.Navigator>
  );
}

export default function AppNavigator() {
  const { user, isLoading } = useAuth();

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Main" component={MainTabs} />
      <Stack.Screen name="Administration" component={AdministrationScreen} />
      <Stack.Screen name="Login" component={LoginScreen} />
    </Stack.Navigator>
  );
}

