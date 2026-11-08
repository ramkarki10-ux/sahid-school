import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  Image,
  TouchableOpacity,
  TextInput,
  Modal,
  ActivityIndicator,
  RefreshControl,
  Share,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../theme/colors';
import { ApiService } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function FeedScreen() {
  const { user } = useAuth();
  const [posts, setPosts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Create post modal state
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [postContent, setPostContent] = useState('');
  const [postType, setPostType] = useState('post');
  const [submitting, setSubmitting] = useState(false);

  // Comment state
  const [activeCommentPostId, setActiveCommentPostId] = useState<number | null>(null);
  const [commentText, setCommentText] = useState('');

  const loadFeed = useCallback(async () => {
    try {
      const feedPosts = await ApiService.getFeed();
      setPosts(feedPosts);
    } catch (err) {
      console.error('Error loading feed:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadFeed();
  }, [loadFeed]);

  const onRefresh = () => {
    setRefreshing(true);
    loadFeed();
  };

  const handleLike = async (postId: number) => {
    try {
      const res = await ApiService.toggleLike(postId);
      setPosts((prev) =>
        prev.map((p) =>
          p.id === postId
            ? { ...p, has_liked: res.liked, likes_count: res.likes_count }
            : p
        )
      );
    } catch (err) {
      Alert.alert('त्रुटि', 'लाइक गर्न सकिएन।');
    }
  };

  const handleShare = async (post: any) => {
    try {
      await Share.share({
        message: `${post.author_name} को विद्यालय पोस्ट: ${post.content}\n\nसहिद स्मृति आवासीय मा.वि., इटहरी-१९, सुनसरी`,
        title: 'सहिद स्मृति मा.वि. न्युज फिड',
      });
    } catch (e) {}
  };

  const handleAddComment = async (postId: number) => {
    if (!commentText.trim()) return;
    try {
      const res = await ApiService.addComment(postId, commentText.trim());
      setPosts((prev) =>
        prev.map((p) => {
          if (p.id === postId) {
            const comments = p.comments ? [...p.comments, res.comment] : [res.comment];
            return { ...p, comments, comments_count: res.comments_count };
          }
          return p;
        })
      );
      setCommentText('');
      setActiveCommentPostId(null);
    } catch (err) {
      Alert.alert('त्रुटि', 'कमेन्ट थप्न सकिएन।');
    }
  };

  const handleCreatePost = async () => {
    if (!postContent.trim()) {
      Alert.alert('जानकारी', 'कृपया केही विवरण लेख्नुहोस्।');
      return;
    }
    setSubmitting(true);
    try {
      await ApiService.createPost(postContent.trim(), undefined, postType);
      setPostContent('');
      setCreateModalVisible(false);
      loadFeed();
      Alert.alert('सफल', 'तपाईंको पोस्ट प्रकाशित भयो!');
    } catch (err) {
      Alert.alert('त्रुटि', 'पोस्ट सिर्जना गर्न सकिएन।');
    } finally {
      setSubmitting(false);
    }
  };

  const renderPost = ({ item }: { item: any }) => {
    const isNotice = item.post_type === 'notice_share';
    const isAchievement = item.post_type === 'achievement';

    return (
      <View style={styles.card}>
        {/* Post Header */}
        <View style={styles.postHeader}>
          <Image
            source={{
              uri:
                item.author_avatar ||
                `https://ui-avatars.com/api/?name=${encodeURIComponent(item.author_name)}&background=1B365D&color=fff`,
            }}
            style={styles.avatar}
          />
          <View style={{ flex: 1, marginLeft: 10 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
              <Text style={styles.authorName}>{item.author_name}</Text>
              <View
                style={[
                  styles.roleBadge,
                  item.author_role === 'SUPER_ADMIN'
                    ? { backgroundColor: '#FEE2E2' }
                    : item.author_role === 'TEACHER'
                    ? { backgroundColor: '#D1FAE5' }
                    : { backgroundColor: '#E0E7FF' },
                ]}
              >
                <Text
                  style={[
                    styles.roleBadgeText,
                    item.author_role === 'SUPER_ADMIN'
                      ? { color: '#B91C1C' }
                      : item.author_role === 'TEACHER'
                      ? { color: '#047857' }
                      : { color: '#4338CA' },
                  ]}
                >
                  {item.author_role}
                </Text>
              </View>
            </View>
            <Text style={styles.postTime}>{item.relative_time || item.created_at?.slice(0, 10)}</Text>
          </View>

          {isAchievement && (
            <View style={styles.typeBadge}>
              <Ionicons name="trophy" size={12} color="#B45309" />
              <Text style={styles.typeBadgeText}>उपलब्धि</Text>
            </View>
          )}
          {isNotice && (
            <View style={[styles.typeBadge, { backgroundColor: '#E0F2FE' }]}>
              <Ionicons name="megaphone" size={12} color="#0369A1" />
              <Text style={[styles.typeBadgeText, { color: '#0369A1' }]}>सूचना</Text>
            </View>
          )}
        </View>

        {/* Content Body */}
        <Text style={styles.postContent}>{item.content}</Text>

        {/* Attached Photo */}
        {item.image_url ? (
          <Image source={{ uri: item.image_url }} style={styles.postImage} resizeMode="cover" />
        ) : null}

        {/* Shared Notice Card */}
        {isNotice && item.notice_title && (
          <View style={styles.sharedNoticeCard}>
            <Ionicons name="newspaper-outline" size={24} color={Colors.gold} />
            <View style={{ flex: 1, marginLeft: 10 }}>
              <Text style={styles.sharedNoticeTitle} numberOfLines={2}>
                {item.notice_title}
              </Text>
              <Text style={styles.sharedNoticeDate}>आधिकारिक विद्यालय सूचना</Text>
            </View>
          </View>
        )}

        {/* Likes & Comments Count */}
        <View style={styles.statsRow}>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <View style={styles.likeIconCircle}>
              <Ionicons name="thumbs-up" size={10} color="#fff" />
            </View>
            <Text style={styles.statsText}>{item.likes_count || 0} जना</Text>
          </View>
          <Text style={styles.statsText}>{item.comments_count || 0} कमेन्टहरू</Text>
        </View>

        {/* Action Bar (Like, Comment, Share) */}
        <View style={styles.actionBar}>
          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => handleLike(item.id)}
          >
            <Ionicons
              name={item.has_liked ? 'thumbs-up' : 'thumbs-up-outline'}
              size={18}
              color={item.has_liked ? Colors.likeBlue : Colors.textMuted}
            />
            <Text
              style={[
                styles.actionBtnText,
                item.has_liked && { color: Colors.likeBlue, fontWeight: 'bold' },
              ]}
            >
              लाइक
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() =>
              setActiveCommentPostId(activeCommentPostId === item.id ? null : item.id)
            }
          >
            <Ionicons name="chatbubble-outline" size={18} color={Colors.textMuted} />
            <Text style={styles.actionBtnText}>कमेन्ट</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.actionBtn} onPress={() => handleShare(item)}>
            <Ionicons name="share-social-outline" size={18} color={Colors.textMuted} />
            <Text style={styles.actionBtnText}>सेयर</Text>
          </TouchableOpacity>
        </View>

        {/* Comment Accordion & List */}
        {activeCommentPostId === item.id && (
          <View style={styles.commentSection}>
            {/* Comments List */}
            {item.comments && item.comments.length > 0 ? (
              item.comments.map((c: any) => (
                <View key={c.id} style={styles.commentItem}>
                  <Image
                    source={{
                      uri:
                        c.user_avatar ||
                        `https://ui-avatars.com/api/?name=${encodeURIComponent(c.user_name)}&background=CBD5E1&color=000`,
                    }}
                    style={styles.commentAvatar}
                  />
                  <View style={styles.commentBubble}>
                    <Text style={styles.commentUser}>{c.user_name}</Text>
                    <Text style={styles.commentBody}>{c.content}</Text>
                  </View>
                </View>
              ))
            ) : (
              <Text style={styles.noCommentsText}>पहिलो कमेन्ट तपाईं नै लेख्नुहोस्!</Text>
            )}

            {/* Comment Input */}
            <View style={styles.commentInputRow}>
              <TextInput
                style={styles.commentInput}
                placeholder="कमेन्ट लेख्नुहोस्..."
                value={commentText}
                onChangeText={setCommentText}
                placeholderTextColor={Colors.textMuted}
              />
              <TouchableOpacity
                style={styles.commentSendBtn}
                onPress={() => handleAddComment(item.id)}
              >
                <Ionicons name="send" size={16} color="#fff" />
              </TouchableOpacity>
            </View>
          </View>
        )}
      </View>
    );
  };

  return (
    <View style={styles.container}>
      {/* Top Header Banner */}
      <View style={styles.header}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <Image
            source={{ uri: 'https://sahid-school.vercel.app/static/images/logo_header.png' }}
            style={styles.schoolLogo}
            resizeMode="contain"
          />
          <View>
            <Text style={styles.headerTitle}>सहिद स्मृति न्युज फिड</Text>
            <Text style={styles.headerSub}>शैक्षिक सामाजिक संवाद पोर्टल</Text>
          </View>
        </View>
        <TouchableOpacity
          style={styles.createBtnHeader}
          onPress={() => setCreateModalVisible(true)}
        >
          <Ionicons name="add" size={20} color="#fff" />
        </TouchableOpacity>
      </View>

      {/* "What's on your mind?" Quick Box */}
      <TouchableOpacity
        style={styles.quickCreateBox}
        onPress={() => setCreateModalVisible(true)}
      >
        <Image
          source={{
            uri:
              user?.avatar ||
              `https://ui-avatars.com/api/?name=${encodeURIComponent(user?.username || 'User')}&background=1B365D&color=fff`,
          }}
          style={styles.smallAvatar}
        />
        <Text style={styles.quickCreateText}>
          {user?.full_name_ne ? `${user.full_name_ne}, ` : ''}तपाईंको मनमा के छ?
        </Text>
        <Ionicons name="images-outline" size={20} color={Colors.primary} />
      </TouchableOpacity>

      {/* Posts Stream */}
      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>न्युज फिड लोड हुँदैछ...</Text>
        </View>
      ) : (
        <FlatList
          data={posts}
          keyExtractor={(item) => item.id.toString()}
          renderItem={renderPost}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[Colors.primary]} />
          }
          contentContainerStyle={{ paddingBottom: 24 }}
        />
      )}

      {/* CREATE POST MODAL */}
      <Modal visible={createModalVisible} animationType="slide" transparent>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={styles.modalOverlay}
        >
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>नयाँ पोस्ट सिर्जना गर्नुहोस्</Text>
              <TouchableOpacity onPress={() => setCreateModalVisible(false)}>
                <Ionicons name="close" size={24} color={Colors.textMain} />
              </TouchableOpacity>
            </View>

            <TextInput
              style={styles.modalInput}
              placeholder="विद्यालय परिवारसँग केही सेयर गर्न चाहनुहुन्छ?..."
              placeholderTextColor={Colors.textMuted}
              multiline
              numberOfLines={4}
              value={postContent}
              onChangeText={setPostContent}
            />

            {/* Category Selectors */}
            <View style={styles.categoryRow}>
              {[
                { key: 'post', label: '📝 सामान्य' },
                { key: 'announcement', label: '📢 घोषणा' },
                { key: 'achievement', label: '🏆 उपलब्धि' },
              ].map((c) => (
                <TouchableOpacity
                  key={c.key}
                  style={[
                    styles.catChip,
                    postType === c.key && { backgroundColor: Colors.primary },
                  ]}
                  onPress={() => setPostType(c.key)}
                >
                  <Text
                    style={[
                      styles.catChipText,
                      postType === c.key && { color: '#fff', fontWeight: 'bold' },
                    ]}
                  >
                    {c.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Submit Button */}
            <TouchableOpacity
              style={[styles.modalSubmitBtn, submitting && { opacity: 0.7 }]}
              onPress={handleCreatePost}
              disabled={submitting}
            >
              {submitting ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Text style={styles.modalSubmitText}>पोस्ट गर्नुहोस्</Text>
              )}
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F1F5F9' },
  header: {
    backgroundColor: Colors.primary,
    paddingTop: 45,
    paddingBottom: 15,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  schoolLogo: { width: 34, height: 34 },
  headerTitle: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  headerSub: { color: Colors.gold, fontSize: 11 },
  createBtnHeader: {
    backgroundColor: Colors.gold,
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  quickCreateBox: {
    backgroundColor: '#fff',
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    marginHorizontal: 12,
    marginTop: 10,
    marginBottom: 4,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  smallAvatar: { width: 34, height: 34, borderRadius: 17, marginRight: 10 },
  quickCreateText: { flex: 1, color: Colors.textMuted, fontSize: 13 },
  card: {
    backgroundColor: '#fff',
    marginHorizontal: 12,
    marginTop: 10,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    overflow: 'hidden',
  },
  postHeader: { flexDirection: 'row', alignItems: 'center', padding: 12 },
  avatar: { width: 40, height: 40, borderRadius: 20 },
  authorName: { fontSize: 13, fontWeight: 'bold', color: Colors.textMain },
  roleBadge: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 10 },
  roleBadgeText: { fontSize: 9, fontWeight: 'bold' },
  postTime: { fontSize: 10, color: Colors.textMuted, marginTop: 2 },
  typeBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#FEF3C7',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 12,
  },
  typeBadgeText: { fontSize: 10, fontWeight: 'bold', color: '#B45309' },
  postContent: {
    paddingHorizontal: 14,
    paddingBottom: 10,
    fontSize: 13,
    color: '#1E293B',
    lineHeight: 19,
  },
  postImage: { width: '100%', height: 220, backgroundColor: '#000' },
  sharedNoticeCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFBEB',
    borderWidth: 1,
    borderColor: '#FDE68A',
    borderRadius: 10,
    padding: 10,
    marginHorizontal: 12,
    marginBottom: 10,
  },
  sharedNoticeTitle: { fontSize: 12, fontWeight: 'bold', color: '#92400E' },
  sharedNoticeDate: { fontSize: 10, color: '#B45309', marginTop: 2 },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: '#F1F5F9',
  },
  likeIconCircle: {
    width: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: Colors.likeBlue,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 6,
  },
  statsText: { fontSize: 11, color: Colors.textMuted },
  actionBar: {
    flexDirection: 'row',
    borderTopWidth: 1,
    borderTopColor: '#F1F5F9',
    paddingVertical: 4,
  },
  actionBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 8,
  },
  actionBtnText: { fontSize: 12, color: Colors.textMuted, fontWeight: '600' },
  commentSection: {
    backgroundColor: '#F8FAFC',
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
    padding: 12,
  },
  commentItem: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 8 },
  commentAvatar: { width: 26, height: 26, borderRadius: 13, marginRight: 8, marginTop: 2 },
  commentBubble: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 8,
    flex: 1,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  commentUser: { fontSize: 11, fontWeight: 'bold', color: Colors.textMain },
  commentBody: { fontSize: 11, color: '#334155', marginTop: 2 },
  noCommentsText: { fontSize: 11, color: Colors.textMuted, textAlign: 'center', marginVertical: 6 },
  commentInputRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 6 },
  commentInput: {
    flex: 1,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
    fontSize: 12,
  },
  commentSendBtn: {
    backgroundColor: Colors.primary,
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingContainer: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  loadingText: { marginTop: 10, fontSize: 13, color: Colors.textMuted },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 14,
  },
  modalTitle: { fontSize: 15, fontWeight: 'bold', color: Colors.textMain },
  modalInput: {
    borderWidth: 1,
    borderColor: '#E2E8F0',
    borderRadius: 12,
    padding: 12,
    fontSize: 13,
    minHeight: 100,
    textAlignVertical: 'top',
  },
  categoryRow: { flexDirection: 'row', gap: 8, marginVertical: 14 },
  catChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: '#F1F5F9',
  },
  catChipText: { fontSize: 11, color: Colors.textMain },
  modalSubmitBtn: {
    backgroundColor: Colors.primary,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
  },
  modalSubmitText: { color: '#fff', fontSize: 14, fontWeight: 'bold' },
});
