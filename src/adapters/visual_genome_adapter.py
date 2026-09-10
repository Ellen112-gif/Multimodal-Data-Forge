import json

from src.schema.multimodal_sample import MultimodalSample


class VisualGenomeAdapter:

    def __init__(self, path):
        self.path = path

    def load(self):
        """
        Load Visual Genome subset records
        and convert them to MultimodalSample objects.
        """

        samples = []

        with open(
            self.path,
            "r",
            encoding="utf-8"
        ) as f:

            for index, line in enumerate(
                f,
                start=1
            ):

                line = line.strip()

                if not line:
                    continue

                record = json.loads(line)

                sample = MultimodalSample(
                    sample_id=f"vg_{index:06d}",

                    # Visual Genome 当前没有 character 字段，
                    # 用 source 类型占位即可
                    character="visual_genome",

                    # region description 作为真实场景文本
                    scene=record.get(
                        "text",
                        ""
                    ),

                    # dialogue 对真实 VG 数据没有意义，
                    # 暂时保持空字符串
                    dialogue="",

                    # CLIPAlignmentOperator 需要的文本描述
                    image_prompt=record.get(
                        "text",
                        ""
                    ),

                    emotion="",

                    action="",

                    visual_style="real_image",

                    image_path=record.get(
                        "image_path"
                    ),

                    width=record.get(
                        "width"
                    ),

                    height=record.get(
                        "height"
                    ),

                    status="pending"
                )

                samples.append(sample)

        return samples