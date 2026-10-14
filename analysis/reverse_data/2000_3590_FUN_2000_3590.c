
/* WARNING: Instruction at (ram,0x000235a9) overlaps instruction at (ram,0x000235a8)
    */

void __cdecl16far FUN_2000_3590(byte *param_1)

{
  byte *pbVar1;
  uint *puVar2;
  uint uVar3;
  code *pcVar4;
  byte bVar5;
  undefined1 uVar6;
  uint uVar7;
  undefined2 uVar8;
  int iVar9;
  int in_CX;
  int iVar10;
  undefined2 extraout_DX;
  undefined2 extraout_DX_00;
  undefined2 extraout_DX_01;
  undefined2 extraout_DX_02;
  undefined2 extraout_DX_03;
  undefined2 extraout_DX_04;
  undefined1 *puVar11;
  byte *pbVar12;
  int unaff_DI;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  byte bVar13;
  byte bVar14;
  bool bVar15;
  byte bVar16;
  char cVar17;
  char cVar18;
  char cVar19;
  uint local_4;
  
  puVar11 = &stack0xfffe;
  pcVar4 = (code *)swi(0x3c);
  (*pcVar4)();
  pcVar4 = (code *)swi(0x38);
  (*pcVar4)();
  pcVar4 = (code *)swi(0x39);
  (*pcVar4)();
  while( true ) {
    pcVar4 = (code *)swi(0x3d);
    (*pcVar4)();
    bVar16 = (local_4 & 0x1000) != 0;
    if ((local_4 & 0x4000) == 0) {
      bVar13 = 0;
      if (*(int *)0x39e2 < 0) {
        pcVar4 = (code *)swi(0x39);
        (*pcVar4)();
        pbVar1 = param_1;
        bVar14 = (byte)((uint)param_1 >> 8);
        bVar5 = *pbVar1 - bVar14;
        bVar14 = *pbVar1 < bVar14 || bVar5 < bVar13;
        *pbVar1 = bVar5 - bVar13;
        pcVar4 = (code *)swi(0x38);
        bVar13 = (*pcVar4)();
        cVar17 = (byte)(bVar13 + (9 < (bVar13 & 0xf) | bVar16) * -6 +
                       (0x99 < bVar13 | bVar14) * -0x60) == '\0';
        pcVar4 = (code *)swi(0x35);
        uVar7 = (*pcVar4)();
        in_CX = in_CX + -1;
        if (in_CX != 0 && cVar17 == '\0') goto LAB_2000_3656;
        pcVar4 = (code *)swi(0x3d);
        (*pcVar4)();
        uVar8 = *(undefined2 *)0x39f6;
        *(undefined2 *)0x5356 = *(undefined2 *)0x39f4;
        *(undefined2 *)0x5358 = uVar8;
        uVar7 = *(uint *)0x39f8;
        *(undefined2 *)0x535a = 1;
        if (0 < (int)uVar7) {
          pbVar12 = (byte *)0x3df0;
          iVar9 = *(int *)0x5356;
          *(int *)0x535a = *(int *)0x535a + uVar7;
          puVar2 = (uint *)0x5356;
          uVar3 = *puVar2;
          *puVar2 = *puVar2 + uVar7;
          *(int *)0x5358 = *(int *)0x5358 + ((int)uVar7 >> 0xf) + (uint)CARRY2(uVar3,uVar7);
          do {
            bVar16 = (byte)((uint)param_1 >> 8);
            pcVar4 = (code *)swi(0x39);
            cVar17 = (*pcVar4)();
            pbVar12 = pbVar12 + -1;
            out(extraout_DX,cVar17 + -0x33);
            pcVar4 = (code *)swi(0x38);
            (*pcVar4)();
            *pbVar12 = *pbVar12 | bVar16;
            param_1 = *(byte **)(puVar11 + -2);
            pcVar4 = (code *)swi(0x39);
            (*pcVar4)();
            pcVar4 = (code *)swi(0x38);
            (*pcVar4)();
            pcVar4 = (code *)swi(0x3a);
            (*pcVar4)();
            puVar11 = (undefined1 *)((uint)puVar11 >> 8 | (int)puVar11 << 8);
            cVar17 = (int)puVar11 < 0;
            pcVar4 = (code *)swi(0x39);
            uVar8 = (*pcVar4)();
            bVar5 = ((char)uVar8 + '3') - cVar17;
            bVar15 = CONCAT11((char)((uint)uVar8 >> 8),bVar5) < 0xc783;
            pbVar1 = puVar11 + iVar9 * 0x18 + 0x3a9e;
            bVar16 = *pbVar1;
            bVar13 = *pbVar1;
            *pbVar1 = (bVar13 - bVar5) - bVar15;
            puVar11[iVar9 * 0x18 + 0x451e] =
                 (puVar11[iVar9 * 0x18 + 0x451e] - bVar5) -
                 (bVar16 < bVar5 || (byte)(bVar13 - bVar5) < bVar15);
            uVar7 = uVar7 - 1;
          } while (uVar7 != 0);
        }
      }
      else if ((0 < *(int *)0x39e2) || (*(int *)0x39e0 != 0)) {
        uVar8 = *(undefined2 *)0x39f6;
        *(undefined2 *)0x5356 = *(undefined2 *)0x39f4;
        *(undefined2 *)0x5358 = uVar8;
        uVar7 = *(uint *)0x39f8;
        *(undefined2 *)0x535a = 1;
        if (0 < (int)uVar7) {
          *(undefined2 *)0x5354 = 4;
          *(int *)0x535a = *(int *)0x535a + uVar7;
          puVar2 = (uint *)0x5356;
          uVar3 = *puVar2;
          *puVar2 = *puVar2 + uVar7;
          *(int *)0x5358 = *(int *)0x5358 + ((int)uVar7 >> 0xf) + (uint)CARRY2(uVar3,uVar7);
          pcVar4 = (code *)swi(0x35);
          uVar6 = (*pcVar4)();
          out(extraout_DX_00,uVar6);
          pcVar4 = (code *)swi(0x35);
          uVar6 = (*pcVar4)();
          out(extraout_DX_01,uVar6);
          pcVar4 = (code *)swi(0x35);
          uVar6 = (*pcVar4)();
          out(extraout_DX_02,uVar6);
          pcVar4 = (code *)swi(0x39);
          (*pcVar4)();
          pcVar4 = (code *)swi(0x3d);
          (*pcVar4)();
          do {
            iVar10 = 3;
            pcVar4 = (code *)swi(0x35);
            uVar6 = (*pcVar4)();
            out(extraout_DX_03,uVar6);
            pcVar4 = (code *)swi(0x35);
            uVar6 = (*pcVar4)();
            out(extraout_DX_04,uVar6);
            pcVar4 = (code *)swi(0x39);
            (*pcVar4)();
            pcVar4 = (code *)swi(0x39);
            iVar9 = (*pcVar4)();
          } while (iVar10 != 1 && iVar9 != 0x24be);
          pcVar4 = (code *)swi(0x34);
          (*pcVar4)();
          pcVar4 = (code *)swi(0x39);
          (*pcVar4)();
          pcVar4 = (code *)swi(0x34);
          (*pcVar4)();
          return;
        }
      }
      return;
    }
    if (-1 < *(int *)0x39e2) break;
    pcVar4 = (code *)swi(0x39);
    (*pcVar4)();
    bVar5 = *(byte *)0x3bf0 < (byte)in_CX;
    cVar19 = SBORROW1(*(byte *)0x3bf0,(byte)in_CX);
    pcVar4 = (code *)swi(0x38);
    bVar13 = (*pcVar4)();
    cVar17 = bVar13 + (9 < (bVar13 & 0xf) | bVar16) * -6 + (0x99 < bVar13 | bVar5) * -0x60;
    cVar18 = cVar17 < '\0';
    bVar15 = cVar17 == '\0';
    pcVar4 = (code *)swi(0x35);
    (*pcVar4)();
    in_CX = in_CX + -1;
    if (in_CX == 0 || bVar15 != false) {
      pcVar4 = (code *)swi(0x3d);
      (*pcVar4)();
      *(undefined2 *)0x5356 = 1;
      goto LAB_2000_3601;
    }
    do {
    } while (bVar15 || cVar19 != cVar18);
  }
  if ((*(int *)0x39e2 < 1) && (*(int *)0x39e0 == 0)) {
    return;
  }
  pcVar4 = (code *)swi(0x39);
  (*pcVar4)();
  pcVar4 = (code *)swi(0x39);
  (*pcVar4)();
  pcVar4 = (code *)swi(0x3d);
  (*pcVar4)();
  *(undefined2 *)0x5356 = 3;
LAB_2000_3601:
  *(undefined2 *)0x5358 = 0;
  *(undefined2 *)0x5354 = *(undefined2 *)0x39f4;
  in_CX = *(int *)0x39f8;
  *(undefined2 *)0x535a = 1;
  if (in_CX < 1) {
    return;
  }
  unaff_DI = *(int *)0x5354 * 0x18 + *(int *)0x5356 * 8 + 0x3d10;
  *(int *)0x535a = *(int *)0x535a + in_CX;
  *(int *)0x5354 = *(int *)0x5354 + in_CX;
  do {
    pcVar4 = (code *)swi(0x39);
    uVar7 = (*pcVar4)();
    cVar17 = 0xc732 < uVar7;
    pcVar4 = (code *)swi(0x39);
    uVar8 = (*pcVar4)();
    uVar7 = CONCAT11((char)((uint)uVar8 >> 8),((char)uVar8 + '3') - cVar17);
LAB_2000_3656:
    (&stack0x08c4)[unaff_DI] = ((&stack0x08c4)[unaff_DI] - (char)uVar7) - (uVar7 < 0xc783);
    in_CX = in_CX + -1;
  } while (in_CX != 0);
  return;
}

