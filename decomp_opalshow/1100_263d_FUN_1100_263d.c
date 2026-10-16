
void __cdecl16near FUN_1100_263d(void)

{
  byte *pbVar1;
  bool bVar2;
  byte bVar3;
  byte bVar5;
  byte extraout_AH;
  uint uVar4;
  byte extraout_AH_00;
  byte bVar6;
  undefined2 extraout_DX;
  undefined2 extraout_DX_00;
  uint in_BX;
  byte *pbVar8;
  undefined2 uVar9;
  undefined2 unaff_DS;
  bool bVar10;
  undefined2 uVar7;
  
  *(undefined1 *)0x102b = 1;
  uVar9 = (undefined2)((ulong)*(undefined4 *)0x1120 >> 0x10);
  pbVar8 = (byte *)(byte *)*(undefined4 *)0x1120;
  uVar7 = *(undefined2 *)0x111e;
  bVar10 = (char)uVar7 == '\0';
  if ((char)uVar7 < '\0') goto LAB_1100_2674;
  do {
    bVar5 = 0;
    do {
      bVar6 = (byte)uVar7;
      bVar5 = bVar5 | bVar6;
      in_BX = in_BX - 1;
      if (in_BX == 0) {
        if (*(char *)0x1125 != '\0') {
          FUN_1100_26e1();
          uVar7 = extraout_DX_00;
          bVar5 = extraout_AH_00;
        }
        *pbVar8 = *pbVar8 ^ ((byte)((uint)uVar7 >> 8) ^ *pbVar8) & bVar5;
        return;
      }
      bVar3 = *(byte *)0x2fd & 7;
      bVar6 = bVar6 >> bVar3 | bVar6 << 8 - bVar3;
      uVar7 = CONCAT11((char)((uint)uVar7 >> 8),bVar6);
    } while (!(bool)(((*(byte *)0x2fd & 0x1f) != 0) * ((char)bVar6 < '\0')));
    if (*(char *)0x1125 != '\0') {
      FUN_1100_26e1();
      uVar7 = extraout_DX;
      bVar5 = extraout_AH;
    }
    *pbVar8 = *pbVar8 ^ ((byte)((uint)uVar7 >> 8) ^ *pbVar8) & bVar5;
    pbVar8 = pbVar8 + 1;
    bVar10 = pbVar8 == (byte *)0x0;
LAB_1100_2674:
    uVar4 = in_BX >> (*(byte *)0x305 & 0x1f);
    bVar2 = (*(byte *)0x305 & 0x1f) != 0;
    if (!(bool)(!bVar2 & bVar10 | (bVar2 && uVar4 == 0))) {
      bVar5 = (byte)((uint)uVar7 >> 8);
      if (*(char *)0x1125 == '\0') {
        for (; uVar4 != 0; uVar4 = uVar4 - 1) {
          pbVar1 = pbVar8;
          pbVar8 = pbVar8 + 1;
          *pbVar1 = bVar5;
        }
      }
      else {
        bVar6 = *(byte *)0x10e2;
        if (*(char *)0x2fd == '\x02') {
          do {
            *pbVar8 = *pbVar8 ^ (bVar5 ^ *pbVar8) &
                                *(byte *)(((uint)bVar6 << 1 | (uint)(((uint)pbVar8 & 1) != 0)) +
                                         0x1013);
            pbVar8 = pbVar8 + 1;
            uVar4 = uVar4 - 1;
          } while (uVar4 != 0);
        }
        else {
          do {
            *pbVar8 = *pbVar8 ^ (bVar5 ^ *pbVar8) & *(byte *)(bVar6 + 0x1013);
            pbVar8 = pbVar8 + 1;
            uVar4 = uVar4 - 1;
          } while (uVar4 != 0);
        }
      }
    }
    in_BX = in_BX & *(uint *)0x306;
  } while (in_BX != 0);
  return;
}

