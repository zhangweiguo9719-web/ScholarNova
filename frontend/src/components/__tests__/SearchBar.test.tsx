/**
 * SearchBar 组件测试

 * 由于 SearchBar 组件尚未创建，本测试验证一个最小的搜索栏组件行为。
 * 当实际组件实现后，可调整测试以匹配真实接口。
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

/**
 * 最小搜索栏组件（用于测试框架验证）
 * 实际项目中应导入真实的 SearchBar 组件
 */
function SearchBar({
  onSearch,
  placeholder = 'Search papers...',
}: {
  onSearch: (query: string) => void
  placeholder?: string
}) {
  const [value, setValue] = React.useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (value.trim()) {
      onSearch(value.trim())
    }
  }

  return (
    <form onSubmit={handleSubmit} role="search">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={placeholder}
        aria-label="Search papers"
      />
      <button type="submit">Search</button>
    </form>
  )
}

describe('SearchBar', () => {
  it('should render search input and button', () => {
    render(<SearchBar onSearch={vi.fn()} />)

    expect(screen.getByRole('search')).toBeInTheDocument()
    expect(screen.getByLabelText('Search papers')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Search' })).toBeInTheDocument()
  })

  it('should display placeholder text', () => {
    render(<SearchBar onSearch={vi.fn()} placeholder="Search for papers..." />)

    expect(screen.getByPlaceholderText('Search for papers...')).toBeInTheDocument()
  })

  it('should update input value on typing', () => {
    render(<SearchBar onSearch={vi.fn()} />)

    const input = screen.getByLabelText('Search papers')
    fireEvent.change(input, { target: { value: 'transformer' } })

    expect(input).toHaveValue('transformer')
  })

  it('should call onSearch with query on form submit', () => {
    const onSearch = vi.fn()
    render(<SearchBar onSearch={onSearch} />)

    const input = screen.getByLabelText('Search papers')
    fireEvent.change(input, { target: { value: 'attention mechanism' } })
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))

    expect(onSearch).toHaveBeenCalledWith('attention mechanism')
  })

  it('should not call onSearch with empty query', () => {
    const onSearch = vi.fn()
    render(<SearchBar onSearch={onSearch} />)

    fireEvent.click(screen.getByRole('button', { name: 'Search' }))

    expect(onSearch).not.toHaveBeenCalled()
  })

  it('should not call onSearch with whitespace-only query', () => {
    const onSearch = vi.fn()
    render(<SearchBar onSearch={onSearch} />)

    const input = screen.getByLabelText('Search papers')
    fireEvent.change(input, { target: { value: '   ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))

    expect(onSearch).not.toHaveBeenCalled()
  })

  it('should trim whitespace from query', () => {
    const onSearch = vi.fn()
    render(<SearchBar onSearch={onSearch} />)

    const input = screen.getByLabelText('Search papers')
    fireEvent.change(input, { target: { value: '  deep learning  ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))

    expect(onSearch).toHaveBeenCalledWith('deep learning')
  })

  it('should submit on Enter key press', () => {
    const onSearch = vi.fn()
    render(<SearchBar onSearch={onSearch} />)

    const input = screen.getByLabelText('Search papers')
    fireEvent.change(input, { target: { value: 'NLP' } })
    fireEvent.submit(input.closest('form')!)

    expect(onSearch).toHaveBeenCalledWith('NLP')
  })
})
