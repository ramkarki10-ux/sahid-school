import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  Image,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../theme/colors';
import { useAuth } from '../context/AuthContext';

export default function LoginScreen({ navigation }: any) {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedRole, setSelectedRole] = useState('ALL');

  const handleLogin = async () => {
    if (!username.trim() || !password) {
      Alert.alert('जानकारी', 'कृपया युजरनेम र पासवर्ड दुवै भर्नुहोस्।');
      return;
    }
    setLoading(true);
    try {
      await login(username.trim(), password);
    } catch (e: any) {
      Alert.alert(
        'लगइन असफल',
        e?.response?.data?.detail || 'गलत युजरनेम वा पासवर्ड। कृपया पुनः प्रयास गर्नुहोस्।'
      );
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = (u: string, p: string, r: string) => {
    setUsername(u);
    setPassword(p);
    setSelectedRole(r);
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Brand Logo & Name */}
        <View style={styles.brandBox}>
          <Image
            source={{ uri: 'https://sahid-school.vercel.app/static/images/logo_header.png' }}
            style={styles.logo}
            resizeMode="contain"
          />
          <Text style={styles.schoolName}>सहिद स्मृति आवासीय मा.वि.</Text>
          <Text style={styles.tagline}>स्मार्ट विद्यालय मोबाइल पोर्टल</Text>
        </View>

        {/* Card */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>लगइन गर्नुहोस् (Login)</Text>
          <Text style={styles.cardSubtitle}>
            एडमिन, शिक्षक, विद्यार्थी तथा अभिभावकका लागि एकीकृत पहुँच
          </Text>

          {/* Quick Role Fillers */}
          <View style={styles.roleChips}>
            {[
              { label: 'प्रमुख एडमिन', u: 'admin', p: 'admin123', r: 'ADMIN' },
              { label: 'शिक्षक', u: '9842552857', p: 'password123', r: 'TEACHER' },
              { label: 'विद्यार्थी', u: '9852033133', p: 'password123', r: 'STUDENT' },
              { label: 'अभिभावक', u: '9812345678', p: 'password123', r: 'PARENT' },
            ].map((item) => (
              <TouchableOpacity
                key={item.label}
                style={[
                  styles.chip,
                  selectedRole === item.r && { backgroundColor: Colors.primary },
                ]}
                onPress={() => fillDemo(item.u, item.p, item.r)}
              >
                <Text
                  style={[
                    styles.chipText,
                    selectedRole === item.r && { color: '#fff', fontWeight: 'bold' },
                  ]}
                >
                  {item.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Username / Phone */}
          <View style={styles.inputContainer}>
            <Ionicons name="person-outline" size={18} color={Colors.textMuted} style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="युजरनेम वा मोबाइल नम्बर"
              placeholderTextColor={Colors.textMuted}
              value={username}
              onChangeText={setUsername}
              autoCapitalize="none"
            />
          </View>

          {/* Password */}
          <View style={styles.inputContainer}>
            <Ionicons name="lock-closed-outline" size={18} color={Colors.textMuted} style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="पासवर्ड"
              placeholderTextColor={Colors.textMuted}
              secureTextEntry={!showPassword}
              value={password}
              onChangeText={setPassword}
            />
            <TouchableOpacity onPress={() => setShowPassword(!showPassword)}>
              <Ionicons
                name={showPassword ? 'eye-off-outline' : 'eye-outline'}
                size={18}
                color={Colors.textMuted}
              />
            </TouchableOpacity>
          </View>

          {/* Login Button */}
          <TouchableOpacity
            style={[styles.loginBtn, loading && { opacity: 0.7 }]}
            onPress={handleLogin}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                <Ionicons name="log-in-outline" size={18} color="#fff" />
                <Text style={styles.loginBtnText}>प्रवेश गर्नुहोस् (Login)</Text>
              </View>
            )}
          </TouchableOpacity>
        </View>

        {/* Footer info */}
        <Text style={styles.footerNote}>
          इटहरी-१९, सुनसरी, कोशी प्रदेश, नेपाल • स्थापना: २०६३
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.primary },
  scroll: { flexGrow: 1, justifyContent: 'center', padding: 20 },
  brandBox: { alignItems: 'center', marginBottom: 20 },
  logo: { width: 70, height: 70, marginBottom: 8 },
  schoolName: { fontSize: 18, fontWeight: 'bold', color: '#fff' },
  tagline: { fontSize: 12, color: Colors.gold, marginTop: 2 },
  card: {
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 22,
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 4,
  },
  cardTitle: { fontSize: 16, fontWeight: 'bold', color: Colors.textMain },
  cardSubtitle: { fontSize: 11, color: Colors.textMuted, marginTop: 2, marginBottom: 14 },
  roleChips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 16 },
  chip: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 14,
    backgroundColor: '#F1F5F9',
  },
  chipText: { fontSize: 10, color: Colors.textMain },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E2E8F0',
    borderRadius: 12,
    paddingHorizontal: 12,
    marginBottom: 12,
    backgroundColor: '#F8FAFC',
  },
  inputIcon: { marginRight: 8 },
  input: { flex: 1, height: 46, fontSize: 13, color: Colors.textMain },
  loginBtn: {
    backgroundColor: Colors.primary,
    borderRadius: 12,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 8,
  },
  loginBtnText: { color: '#fff', fontSize: 14, fontWeight: 'bold' },
  footerNote: { textAlign: 'center', color: '#94A3B8', fontSize: 11, marginTop: 24 },
});
