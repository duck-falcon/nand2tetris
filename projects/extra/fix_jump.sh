#!/bin/bash
# ★番号のジャンプ先アドレスを自動計算して2進数に書き換える
# 使い方: ./fix_jumps.sh input.hack > output.hack

if [ -z "$1" ]; then
  echo "Usage: $0 input.hack" >&2
  exit 1
fi

INPUT="$1"

# Pass 1: コメント専用行を除いたバイナリ行に行番号を振り、★N の定義位置を記録
declare -A STAR_ADDR

LINE_NUM=0
while IFS= read -r line; do
  # バイナリ行かどうか: 先頭が0か1で始まる行
  if [[ "$line" =~ ^[01] ]]; then
    # この行に★定義があるか
    # 定義: コメント部分で (★N) の括弧なしで出てくるもの（参照は必ず (★N) の形式）
    COMMENT="${line#*//}"
    if [[ "$COMMENT" =~ [^\(]★([0-9]+)[[:space:]] ]] || [[ "$COMMENT" =~ ^★([0-9]+)[[:space:]] ]]; then
      STAR_ID="${BASH_REMATCH[1]}"
      STAR_ADDR[$STAR_ID]=$LINE_NUM
    fi
    LINE_NUM=$((LINE_NUM + 1))
  fi
done < "$INPUT"

# デバッグ: 定義一覧を出力
for key in $(echo "${!STAR_ADDR[@]}" | tr ' ' '\n' | sort -n); do
  echo "★${key} = ${STAR_ADDR[$key]}" >&2
done

# 数値を16ビット2進数に変換する関数
to_bin16() {
  local n=$1
  local result=""
  for i in $(seq 15 -1 0); do
    if (( n & (1 << i) )); then
      result="${result}1"
    else
      result="${result}0"
    fi
  done
  echo "$result"
}

# Pass 2: 参照側の (★N) を書き換え
while IFS= read -r line; do
  if [[ "$line" =~ ^[01] ]] && [[ "$line" =~ \(★([0-9]+)\) ]]; then
    STAR_ID="${BASH_REMATCH[1]}"
    if [ -n "${STAR_ADDR[$STAR_ID]}" ]; then
      ADDR=${STAR_ADDR[$STAR_ID]}
      NEW_BIN=$(to_bin16 $ADDR)
      # バイナリ部分（先頭16文字）を新しい値に置換
      OLD_BIN="${line:0:16}"
      # コメント部分の @数値(★N) も更新
      line="${NEW_BIN}${line:16}"
      line=$(echo "$line" | sed "s/@[0-9]*(★${STAR_ID})/@${ADDR}(★${STAR_ID})/g")
    fi
  fi
  echo "$line"
done < "$INPUT"
