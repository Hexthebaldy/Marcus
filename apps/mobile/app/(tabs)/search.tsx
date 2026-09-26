import { Text } from "react-native";
import { Screen, styles as s, Empty } from "../../src/ui";
export default function Search() {
  return (
    <Screen>
      <Text style={s.eyebrow}>FIND YOUR NEXT STOP</Text>
      <Text style={s.title}>搜索</Text>
      <Empty
        title="更多城市线索，正在整理"
        body="搜索和主题合辑将在后续开放。现在先去 Discover，看看编辑精选和大家的城市笔记。"
      />
    </Screen>
  );
}
