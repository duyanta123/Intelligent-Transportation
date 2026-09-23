/**
 * 列表请求竞态防护：慢网下快速切换筛选/翻页时，先发出的旧请求可能后返回并覆盖新结果。
 * 每次 load 前 begin() 取号；响应回来时 isCurrent() 判断自己是否仍是最新一次请求，
 * 非最新则丢弃（loading 也交由最新请求管理）。
 */
export function sequenceGuard() {
  let current = 0
  return {
    begin: () => ++current,
    isCurrent: (seq: number) => seq === current,
  }
}
