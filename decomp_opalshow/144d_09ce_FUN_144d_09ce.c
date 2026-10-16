
uint __cdecl16far FUN_144d_09ce(byte *param_1,byte *param_2,uint param_3)

{
  byte *pbVar1;
  byte *pbVar2;
  uint uVar3;
  uint uVar4;
  byte *pbVar5;
  byte *pbVar6;
  int iVar7;
  int iVar8;
  bool bVar9;
  bool bVar10;
  
  if (param_3 == 0) {
    return 0;
  }
  iVar8 = (int)((ulong)param_1 >> 0x10);
  pbVar5 = (byte *)param_1;
  iVar7 = (int)((ulong)param_2 >> 0x10);
  pbVar6 = (byte *)param_2;
  do {
    uVar3 = ~(uint)pbVar6;
    uVar3 = ((param_3 - 1) - uVar3 & -(uint)(param_3 - 1 < uVar3)) + uVar3;
    uVar4 = ~(uint)pbVar5;
    uVar3 = (uVar3 - uVar4 & -(uint)(uVar3 < uVar4)) + uVar4 + 1;
    bVar9 = param_3 < uVar3;
    param_3 = param_3 - uVar3;
    bVar10 = param_3 == 0;
    do {
      if (uVar3 == 0) break;
      uVar3 = uVar3 - 1;
      pbVar2 = pbVar6;
      pbVar6 = pbVar6 + 1;
      pbVar1 = pbVar5;
      pbVar5 = pbVar5 + 1;
      bVar9 = *pbVar1 < *pbVar2;
      bVar10 = *pbVar1 == *pbVar2;
    } while (bVar10);
    if (!bVar10) {
      return (1 - (uint)bVar9) - (uint)(bVar9 != 0);
    }
    if (param_3 == 0) {
      return uVar3;
    }
    if (pbVar5 == (byte *)0x0) {
      iVar8 = iVar8 + 0x1000;
    }
    if (pbVar6 == (byte *)0x0) {
      iVar7 = iVar7 + 0x1000;
    }
  } while( true );
}

