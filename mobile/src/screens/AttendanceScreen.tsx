import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../theme/colors';
import { ApiService } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function AttendanceScreen() {
  const { user, isTeacher, isAdmin } = useAuth();
  const [summary, setSummary] = useState<any>(null);
  const [classes, setClasses] = useState<any[]>([]);
  const [selectedClassId, setSelectedClassId] = useState<number>(1);
  const [students, setStudents] = useState<any[]>([]);
  const [attendanceState, setAttendanceState] = useState<{ [id: number]: string }>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const canMark = isTeacher || isAdmin;

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [sum, clsList] = await Promise.all([
        ApiService.getAttendanceSummary(),
        ApiService.getClasses(),
      ]);
      setSummary(sum);
      setClasses(clsList);

      if (clsList.length > 0) {
        const firstClsId = clsList[0].id;
        setSelectedClassId(firstClsId);
        await loadClassStudents(firstClsId);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadClassStudents = async (classId: number) => {
    try {
      const res = await ApiService.getClassAttendance(classId);
      setStudents(res.students || []);
      // Map initial attendance states
      const stateMap: { [id: number]: string } = {};
      (res.students || []).forEach((s: any) => {
        stateMap[s.student_id] = s.attendance_status || 'PRESENT';
      });
      setAttendanceState(stateMap);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleClassChange = (classId: number) => {
    setSelectedClassId(classId);
    loadClassStudents(classId);
  };

  const setStatus = (studentId: number, status: string) => {
    if (!canMark) return;
    setAttendanceState((prev) => ({ ...prev, [studentId]: status }));
  };

  const markAll = (status: string) => {
    if (!canMark) return;
    const updated: { [id: number]: string } = {};
    students.forEach((s) => {
      updated[s.student_id] = status;
    });
    setAttendanceState(updated);
  };

  const saveAttendance = async () => {
    if (!canMark) {
      Alert.alert('अनुमति छैन', 'हाजिरी परिवर्तन गर्ने अधिकार शिक्षक वा एडमिनलाई मात्र छ।');
      return;
    }
    setSubmitting(true);
    const today = new Date().toISOString().slice(0, 10);
    const records = students.map((s) => ({
      student_id: s.student_id,
      status: attendanceState[s.student_id] || 'PRESENT',
    }));

    try {
      await ApiService.markAttendance(selectedClassId, today, records);
      Alert.alert('सफल!', 'दैनिक हाजिरी सफलतापूर्वक सुरक्षित भयो।');
      const sum = await ApiService.getAttendanceSummary();
      setSummary(sum);
    } catch (e) {
      Alert.alert('त्रुटि', 'हाजिरी सेभ गर्न सकिएन।');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <View style={styles.container}>
      {/* Header Banner */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>स्मार्ट हाजिरी ट्र्याकर</Text>
        <Text style={styles.headerSub}>दैनिक विद्यार्थी तथा शिक्षक हाजिरी व्यवस्थापन</Text>
      </View>

      {loading ? (
        <View style={styles.centerLoading}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>हाजिरी विवरण लोड हुँदैछ...</Text>
        </View>
      ) : (
        <ScrollView contentContainerStyle={{ paddingBottom: 30 }}>
          {/* Summary Stat Cards */}
          {summary && (
            <View style={styles.summaryContainer}>
              <View style={[styles.statBox, { borderColor: '#DBEAFE', backgroundColor: '#EFF6FF' }]}>
                <Text style={[styles.statNum, { color: Colors.primary }]}>
                  {summary.total_students}
                </Text>
                <Text style={styles.statLabel}>कुल विद्यार्थी</Text>
              </View>

              <View style={[styles.statBox, { borderColor: '#D1FAE5', backgroundColor: '#ECFDF5' }]}>
                <Text style={[styles.statNum, { color: Colors.success }]}>
                  {summary.present}
                </Text>
                <Text style={styles.statLabel}>उपस्थित (Present)</Text>
              </View>

              <View style={[styles.statBox, { borderColor: '#FEE2E2', backgroundColor: '#FEF2F2' }]}>
                <Text style={[styles.statNum, { color: Colors.danger }]}>
                  {summary.absent}
                </Text>
                <Text style={styles.statLabel}>अनुपस्थित</Text>
              </View>

              <View style={[styles.statBox, { borderColor: '#FEF3C7', backgroundColor: '#FFFBEB' }]}>
                <Text style={[styles.statNum, { color: Colors.warning }]}>
                  {summary.leave}
                </Text>
                <Text style={styles.statLabel}>बिदा (Leave)</Text>
              </View>
            </View>
          )}

          {/* Class Selector Bar */}
          <View style={styles.classBar}>
            <Text style={styles.sectionTitle}>कक्षा छनोट गर्नुहोस्:</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginTop: 8 }}>
              {classes.map((c) => (
                <TouchableOpacity
                  key={c.id}
                  style={[
                    styles.classChip,
                    selectedClassId === c.id && { backgroundColor: Colors.primary },
                  ]}
                  onPress={() => handleClassChange(c.id)}
                >
                  <Text
                    style={[
                      styles.classChipText,
                      selectedClassId === c.id && { color: '#fff', fontWeight: 'bold' },
                    ]}
                  >
                    {c.class_name_ne}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>

          {/* Quick Mark All Row for Teachers */}
          {canMark && (
            <View style={styles.quickMarkRow}>
              <Text style={{ fontSize: 12, fontWeight: 'bold', color: Colors.textMain }}>
                एकमुष्ट छनोट:
              </Text>
              <View style={{ flexDirection: 'row', gap: 6 }}>
                <TouchableOpacity
                  style={[styles.smallActionBtn, { backgroundColor: '#DCFCE7' }]}
                  onPress={() => markAll('PRESENT')}
                >
                  <Text style={{ color: '#166534', fontSize: 11, fontWeight: 'bold' }}>
                    सबै उपस्थित
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.smallActionBtn, { backgroundColor: '#FEE2E2' }]}
                  onPress={() => markAll('ABSENT')}
                >
                  <Text style={{ color: '#991B1B', fontSize: 11, fontWeight: 'bold' }}>
                    सबै अनुपस्थित
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
          )}

          {/* Students Attendance List */}
          <View style={styles.listContainer}>
            <View style={styles.listHeaderRow}>
              <Text style={[styles.colHeader, { width: 40 }]}>रोल</Text>
              <Text style={[styles.colHeader, { flex: 1 }]}>विद्यार्थीको नाम</Text>
              <Text style={[styles.colHeader, { width: 140, textAlign: 'center' }]}>
                दैनिक स्थिति
              </Text>
            </View>

            {students.length > 0 ? (
              students.map((item) => {
                const cur = attendanceState[item.student_id] || 'PRESENT';
                return (
                  <View key={item.student_id} style={styles.studentRow}>
                    <Text style={styles.rollNum}>{item.roll_no || '-'}</Text>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.studentName}>{item.name_nepali}</Text>
                      <Text style={styles.admNo}>ID: {item.admission_no}</Text>
                    </View>

                    {/* Attendance 3-State Buttons */}
                    <View style={styles.toggleGroup}>
                      <TouchableOpacity
                        style={[
                          styles.toggleBtn,
                          cur === 'PRESENT' && { backgroundColor: Colors.success },
                        ]}
                        onPress={() => setStatus(item.student_id, 'PRESENT')}
                        disabled={!canMark}
                      >
                        <Text
                          style={[
                            styles.toggleBtnText,
                            cur === 'PRESENT' && { color: '#fff', fontWeight: 'bold' },
                          ]}
                        >
                          P
                        </Text>
                      </TouchableOpacity>

                      <TouchableOpacity
                        style={[
                          styles.toggleBtn,
                          cur === 'ABSENT' && { backgroundColor: Colors.danger },
                        ]}
                        onPress={() => setStatus(item.student_id, 'ABSENT')}
                        disabled={!canMark}
                      >
                        <Text
                          style={[
                            styles.toggleBtnText,
                            cur === 'ABSENT' && { color: '#fff', fontWeight: 'bold' },
                          ]}
                        >
                          A
                        </Text>
                      </TouchableOpacity>

                      <TouchableOpacity
                        style={[
                          styles.toggleBtn,
                          cur === 'LEAVE' && { backgroundColor: Colors.warning },
                        ]}
                        onPress={() => setStatus(item.student_id, 'LEAVE')}
                        disabled={!canMark}
                      >
                        <Text
                          style={[
                            styles.toggleBtnText,
                            cur === 'LEAVE' && { color: '#fff', fontWeight: 'bold' },
                          ]}
                        >
                          L
                        </Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                );
              })
            ) : (
              <Text style={styles.emptyText}>यो कक्षामा विद्यार्थीहरू फेला परेनन्।</Text>
            )}
          </View>

          {/* Submit Attendance Button */}
          {canMark && students.length > 0 && (
            <TouchableOpacity
              style={[styles.saveBtn, submitting && { opacity: 0.7 }]}
              onPress={saveAttendance}
              disabled={submitting}
            >
              {submitting ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <Ionicons name="cloud-upload" size={18} color="#fff" />
                  <Text style={styles.saveBtnText}>हाजिरी सुरक्षित गर्नुहोस्</Text>
                </View>
              )}
            </TouchableOpacity>
          )}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  header: {
    backgroundColor: Colors.primary,
    paddingTop: 45,
    paddingBottom: 15,
    paddingHorizontal: 16,
  },
  headerTitle: { color: '#fff', fontSize: 17, fontWeight: 'bold' },
  headerSub: { color: Colors.gold, fontSize: 11, marginTop: 2 },
  centerLoading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  loadingText: { marginTop: 10, fontSize: 12, color: Colors.textMuted },
  summaryContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    padding: 12,
  },
  statBox: {
    flex: 1,
    minWidth: '45%',
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: 'center',
  },
  statNum: { fontSize: 20, fontWeight: 'bold' },
  statLabel: { fontSize: 10, color: Colors.textMuted, marginTop: 2 },
  classBar: { paddingHorizontal: 12, marginTop: 4 },
  sectionTitle: { fontSize: 12, fontWeight: 'bold', color: Colors.textMain },
  classChip: {
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 20,
    backgroundColor: '#E2E8F0',
    marginRight: 6,
  },
  classChipText: { fontSize: 11, color: Colors.textMain },
  quickMarkRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 14,
    marginTop: 14,
  },
  smallActionBtn: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
  },
  listContainer: {
    backgroundColor: '#fff',
    marginHorizontal: 12,
    marginTop: 10,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    overflow: 'hidden',
  },
  listHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F1F5F9',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  colHeader: { fontSize: 11, fontWeight: 'bold', color: Colors.textMuted },
  studentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
  },
  rollNum: { width: 34, fontSize: 12, fontWeight: 'bold', color: Colors.primary },
  studentName: { fontSize: 12, fontWeight: 'bold', color: Colors.textMain },
  admNo: { fontSize: 10, color: Colors.textMuted, marginTop: 1 },
  toggleGroup: { flexDirection: 'row', gap: 4, width: 130, justifyContent: 'flex-end' },
  toggleBtn: {
    width: 34,
    height: 32,
    borderRadius: 8,
    backgroundColor: '#F1F5F9',
    alignItems: 'center',
    justifyContent: 'center',
  },
  toggleBtnText: { fontSize: 12, fontWeight: 'bold', color: Colors.textMuted },
  saveBtn: {
    backgroundColor: Colors.primary,
    marginHorizontal: 12,
    marginTop: 16,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 2,
  },
  saveBtnText: { color: '#fff', fontSize: 14, fontWeight: 'bold' },
  emptyText: { padding: 24, textAlign: 'center', color: Colors.textMuted, fontSize: 12 },
});

