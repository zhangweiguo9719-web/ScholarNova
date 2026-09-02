import { beforeEach, describe, expect, it } from 'vitest'
import { useAssistantStore } from '@/stores/assistantStore'

describe('assistant workspace', () => {
  beforeEach(() => {
    localStorage.clear()
    useAssistantStore.setState({
      folders: [],
      conversations: [{
        id: 'chat-a', folderId: null, title: '新对话', messages: [], createdAt: 1, updatedAt: 1,
      }],
      activeConversationId: 'chat-a',
    })
  })

  it('keeps conversation context isolated by research folder', () => {
    const folderId = useAssistantStore.getState().createFolder('交通预测')
    const chatB = useAssistantStore.getState().createConversation(folderId)
    useAssistantStore.getState().appendMessage('chat-a', { id: 'm1', role: 'user', content: '问题 A' })
    useAssistantStore.getState().appendMessage(chatB, { id: 'm2', role: 'user', content: '问题 B' })

    const state = useAssistantStore.getState()
    expect(state.conversations.find((chat) => chat.id === 'chat-a')?.messages[0].content).toBe('问题 A')
    expect(state.conversations.find((chat) => chat.id === chatB)?.messages[0].content).toBe('问题 B')
    expect(state.conversations.find((chat) => chat.id === chatB)?.folderId).toBe(folderId)
  })

  it('moves chats to unfiled instead of deleting them with a folder', () => {
    const folderId = useAssistantStore.getState().createFolder('材料')
    const chatId = useAssistantStore.getState().createConversation(folderId)

    useAssistantStore.getState().deleteFolder(folderId)

    expect(useAssistantStore.getState().conversations.find((chat) => chat.id === chatId)?.folderId).toBeNull()
  })
})
