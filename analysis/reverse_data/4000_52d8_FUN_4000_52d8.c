
void __cdecl16far
FUN_4000_52d8(undefined2 *param_1,int param_2,undefined2 param_3,int param_4,undefined2 param_5)

{
  int *piVar1;
  undefined2 uVar2;
  char *pcVar3;
  undefined2 in_DX;
  undefined2 *puVar4;
  int iVar5;
  char *pcVar6;
  undefined2 uVar7;
  undefined2 unaff_DS;
  
  uVar7 = (undefined2)((ulong)param_1 >> 0x10);
  puVar4 = (undefined2 *)param_1;
  uVar2 = FUN_4000_54d9(*param_1,puVar4[1],puVar4[2],puVar4[3]);
  *(undefined2 *)0x6486 = uVar2;
  *(undefined2 *)0x6488 = in_DX;
  piVar1 = (int *)*(undefined4 *)0x6486;
  uVar2 = (undefined2)((ulong)piVar1 >> 0x10);
  *(int *)0x1daa = ((int *)piVar1)[1] + -1;
  pcVar3 = (char *)((uint)(*piVar1 == 0x2d) + param_2);
  FUN_4000_6e32(pcVar3,param_3,param_4,(int *)piVar1,uVar2);
  iVar5 = *(int *)((int)*(undefined4 *)0x6486 + 2) + -1;
  *(bool *)0x1dac = *(int *)0x1daa < iVar5;
  *(int *)0x1daa = iVar5;
  if ((-5 < iVar5) && (iVar5 < param_4)) {
    if (*(char *)0x1dac != '\0') {
      do {
        pcVar6 = pcVar3;
        pcVar3 = pcVar6 + 1;
      } while (*pcVar6 != '\0');
      pcVar6[-1] = '\0';
    }
    FUN_4000_52aa(puVar4,uVar7,param_2,param_3,param_4);
    return;
  }
  FUN_4000_5106(puVar4,uVar7,param_2,param_3,param_4,param_5);
  return;
}

